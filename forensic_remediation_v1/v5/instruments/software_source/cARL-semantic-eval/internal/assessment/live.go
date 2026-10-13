package assessment

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptrace"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"sync/atomic"
	"time"
)

// Live transport for the assessment-challenge interface. Exactly one HTTP
// attempt; no retries, redirects, proxies, connection reuse or fallback model.
const (
	LiveSchema        = "carl-assessment-challenge-v2-live-receipt"
	LiveTransportID   = "carl-assessment-challenge-live-transport-v2"
	LiveEndpoint      = "https://api.typesafe.ai/v1/systemone"
	LiveCredentialEnv = "JEVKEY"
	MaxLiveResponse   = 4 << 20
)

const liveIdentityEvidence = "reported_model_field_not_provider_attestation"

type TLSEvidence struct {
	Version               string   `json:"version"`
	CipherSuite           string   `json:"cipher_suite"`
	ServerName            string   `json:"server_name"`
	PeerCertificateSHA256 []string `json:"peer_certificate_sha256"`
	Note                  string   `json:"note"`
}

type LiveReceipt struct {
	Schema                 string              `json:"schema"`
	Transport              string              `json:"transport"`
	Mode                   string              `json:"mode"`
	Status                 string              `json:"status"`
	FailureClass           string              `json:"failure_class,omitempty"`
	Error                  string              `json:"error,omitempty"`
	Prepared               []byte              `json:"prepared"`
	PreparedSHA256         string              `json:"prepared_sha256"`
	Endpoint               string              `json:"endpoint"`
	RequestBody            []byte              `json:"request_body"`
	RequestSHA256          string              `json:"request_sha256"`
	AuthorizationHeader    string              `json:"authorization_header"`
	CredentialSource       string              `json:"credential_source"`
	RequestWritten         bool                `json:"request_written"`
	HTTPStatus             int                 `json:"http_status"`
	ResponseHeaders        map[string][]string `json:"response_headers"`
	RawResponse            []byte              `json:"raw_response"`
	ResponseSHA256         string              `json:"response_sha256"`
	ResponseCapture        string              `json:"response_capture"`
	ResponseBytesObserved  int                 `json:"response_bytes_observed"`
	ResponseObservedSHA256 string              `json:"response_observed_sha256"`
	TLS                    *TLSEvidence        `json:"tls"`
	StartedAt              string              `json:"started_at"`
	CompletedAt            string              `json:"completed_at"`
	LatencyMS              int64               `json:"latency_ms"`
	TimeoutMS              int64               `json:"timeout_ms"`
	Result                 *Decision           `json:"result"`
	ImplementationSHA256   string              `json:"implementation_sha256"`
	LiveCalls              int                 `json:"live_calls"`
	Attempts               int                 `json:"attempts"`
	ReceiptKind            string              `json:"receipt_kind"`
	ProviderAuthenticated  bool                `json:"provider_authenticated"`
	IdentityEvidence       string              `json:"identity_evidence"`
	ProvenanceNotice       string              `json:"provenance_notice"`
}

// LiveTransport is constructed only by NewLiveTransport (production endpoint)
// or by package tests; the command line cannot select another endpoint.
type LiveTransport struct {
	endpoint string
	key      string
	timeout  time.Duration
	client   *http.Client
	now      func() time.Time
}

func newClient(base *http.Transport) *http.Client {
	base.Proxy = nil
	base.DisableKeepAlives = true
	base.DisableCompression = true
	base.ForceAttemptHTTP2 = false
	base.TLSNextProto = map[string]func(string, *tls.Conn) http.RoundTripper{}
	base.MaxIdleConns = 0
	if base.TLSClientConfig == nil {
		base.TLSClientConfig = &tls.Config{}
	}
	base.TLSClientConfig.MinVersion = tls.VersionTLS12
	return &http.Client{Transport: base,
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
}

func NewLiveTransport(key string, timeout time.Duration) *LiveTransport {
	dialer := &net.Dialer{Timeout: timeout}
	return &LiveTransport{endpoint: LiveEndpoint, key: key, timeout: timeout, now: time.Now,
		client: newClient(&http.Transport{DialContext: dialer.DialContext, TLSHandshakeTimeout: timeout})}
}

func certHashes(state *tls.ConnectionState) *TLSEvidence {
	if state == nil {
		return nil
	}
	evidence := &TLSEvidence{Version: tls.VersionName(state.Version), CipherSuite: tls.CipherSuiteName(state.CipherSuite),
		ServerName: state.ServerName, PeerCertificateSHA256: []string{},
		Note: "Transport metadata only; not a provider signature over the response."}
	for _, cert := range state.PeerCertificates {
		sum := sha256.Sum256(cert.Raw)
		evidence.PeerCertificateSHA256 = append(evidence.PeerCertificateSHA256, hex.EncodeToString(sum[:]))
	}
	return evidence
}

func keepHeaders(h http.Header, key string) map[string][]string {
	out := map[string][]string{}
	names := make([]string, 0, len(h))
	for name := range h {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		if strings.EqualFold(name, "Set-Cookie") ||
			(key != "" && strings.Contains(strings.ToLower(name), strings.ToLower(key))) {
			continue
		}
		values := []string{}
		for _, v := range h[name] {
			if key != "" && strings.Contains(v, key) {
				v = "[REDACTED]"
			}
			values = append(values, v)
		}
		out[name] = values
	}
	return out
}

func validCredential(key string) bool {
	padding := false
	for _, c := range key {
		if c == '=' {
			padding = true
			continue
		}
		if padding || !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' ||
			c >= '0' && c <= '9' || strings.ContainsRune("-._~+/", c)) {
			return false
		}
	}
	return key != "" && key[0] != '='
}

// Inspect decoded JSON strings as well as bytes: JSON escaping must not bypass
// credential suppression. Stored bytes are never rewritten into a fake original.
func containsCredential(raw []byte, key string) bool {
	if key == "" {
		return false
	}
	if bytes.Contains(raw, []byte(key)) {
		return true
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	for {
		token, err := d.Token()
		if err != nil {
			return false
		}
		if s, ok := token.(string); ok && strings.Contains(s, key) {
			return true
		}
	}
}

func rejectPreparedCredential(raw []byte, key string) error {
	if strings.TrimSpace(key) == "" {
		return nil
	}
	var p Prepared
	var r Request
	// Inspect nested byte fields before validation errors or input copying.
	_ = json.Unmarshal(raw, &p)
	_ = json.Unmarshal(p.Input, &r)
	if containsCredential(raw, key) || preparedContainsCredential(&p, &r, key) {
		return fmt.Errorf("credential found in prepared input; exact bytes cannot be persisted or sent safely")
	}
	return nil
}

func preparedContainsCredential(p *Prepared, r *Request, key string) bool {
	for _, raw := range [][]byte{p.Input, r.NativeRequest, r.Assessment, r.ParentCheckpoint, r.SourceManifest, []byte(r.Source.Text)} {
		if containsCredential(raw, key) {
			return true
		}
	}
	for name, raw := range p.PolicyFiles {
		if strings.Contains(name, key) || containsCredential(raw, key) {
			return true
		}
	}
	return false
}

// EvaluateLive verifies the prepared artifact, then sends the exact prepared
// native request bytes once. Every outcome is a receipt; failures are first
// attempts and are never retried here.
func EvaluateLive(prepared []byte, anchor, implementation string, t *LiveTransport) (*LiveReceipt, error) {
	if t == nil {
		return nil, fmt.Errorf("live transport required")
	}
	if !hashRE.MatchString(implementation) {
		return nil, fmt.Errorf("implementation digest required")
	}
	if t.timeout < time.Millisecond || t.timeout > 10*time.Minute {
		return nil, fmt.Errorf("timeout must be within [1ms, 10m]")
	}
	if err := rejectPreparedCredential(prepared, t.key); err != nil {
		return nil, err
	}
	p, err := VerifyPrepared(prepared, anchor)
	if err != nil {
		return nil, err
	}
	r, a, native, err := ValidateRequest(p.Input)
	if err != nil {
		return nil, err
	}
	body := append([]byte(nil), r.NativeRequest...)
	receipt := &LiveReceipt{Schema: LiveSchema, Transport: LiveTransportID, Mode: "live", Status: "failed",
		Prepared: prepared, PreparedSHA256: anchor, Endpoint: t.endpoint, RequestBody: body,
		RequestSHA256: Hash(body), AuthorizationHeader: "Bearer [REDACTED]", CredentialSource: "env:" + LiveCredentialEnv,
		ResponseHeaders: map[string][]string{}, RawResponse: []byte{}, TimeoutMS: t.timeout.Milliseconds(),
		ResponseCapture: "not_received", ResponseObservedSHA256: Hash(nil),
		ImplementationSHA256: implementation, Attempts: 1,
		ReceiptKind: "local_integrity_receipt", ProviderAuthenticated: false,
		IdentityEvidence: liveIdentityEvidence,
		ProvenanceNotice: p.ProvenanceNotice}
	started := t.now().UTC()
	receipt.StartedAt = started.Format(time.RFC3339Nano)
	finish := func() *LiveReceipt {
		done := t.now().UTC()
		receipt.CompletedAt = done.Format(time.RFC3339Nano)
		receipt.LatencyMS = done.Sub(started).Milliseconds()
		receipt.ResponseSHA256 = Hash(receipt.RawResponse)
		if receipt.RequestWritten {
			receipt.LiveCalls = 1
		}
		return receipt
	}
	if strings.TrimSpace(t.key) == "" {
		receipt.FailureClass, receipt.Error = "credentials_unavailable", "credential environment variable empty or unset"
		receipt.Attempts = 0
		return finish(), nil
	}
	if !validCredential(t.key) {
		receipt.FailureClass, receipt.Error = "credentials_invalid", "credential is not a valid bearer token"
		receipt.Attempts = 0
		return finish(), nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), t.timeout)
	defer cancel()
	var written atomic.Bool
	trace := &httptrace.ClientTrace{WroteRequest: func(info httptrace.WroteRequestInfo) {
		if info.Err == nil {
			written.Store(true)
		}
	}}
	req, err := http.NewRequestWithContext(httptrace.WithClientTrace(ctx, trace), http.MethodPost, t.endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.GetBody = nil // forbids transport-level body replay
	req.ContentLength = int64(len(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept-Encoding", "identity")
	req.Header.Set("Authorization", "Bearer "+t.key)
	resp, err := t.client.Do(req)
	receipt.RequestWritten = written.Load()
	if err != nil {
		receipt.FailureClass = "network_error"
		switch {
		case errors.Is(err, context.DeadlineExceeded) || isTimeout(err):
			receipt.FailureClass = "timeout"
		}
		receipt.Error = "HTTP exchange failed; provider execution is not established by local write evidence"
		return finish(), nil
	}
	defer resp.Body.Close()
	receipt.RequestWritten = true
	receipt.HTTPStatus = resp.StatusCode
	receipt.ResponseHeaders = keepHeaders(resp.Header, t.key)
	receipt.TLS = certHashes(resp.TLS)
	raw, readErr := io.ReadAll(io.LimitReader(resp.Body, MaxLiveResponse+1))
	receipt.ResponseBytesObserved, receipt.ResponseObservedSHA256 = len(raw), Hash(raw)
	receipt.RawResponse, receipt.ResponseCapture = raw, "complete"
	if containsCredential(raw, t.key) {
		receipt.RawResponse, receipt.ResponseCapture = []byte{}, "withheld_credential"
		receipt.FailureClass, receipt.Error = "credential_echo", "response contained credential material; body withheld, not redacted into an original"
		return finish(), nil
	}
	if encodedResponse(resp.Header) {
		receipt.RawResponse, receipt.ResponseCapture = []byte{}, "withheld_encoding"
		receipt.FailureClass, receipt.Error = "unsupported_response_encoding", "encoded response withheld; no automatic decompression"
		return finish(), nil
	}
	if len(raw) > MaxLiveResponse {
		receipt.RawResponse, receipt.ResponseCapture = raw[:MaxLiveResponse], "truncated"
		receipt.FailureClass, receipt.Error = "response_too_large", "response exceeded transport limit; truncated prefix preserved"
		return finish(), nil
	}
	if readErr != nil {
		receipt.ResponseCapture = "partial"
		receipt.FailureClass = "network_error"
		if errors.Is(readErr, context.DeadlineExceeded) || isTimeout(readErr) {
			receipt.FailureClass = "timeout"
		}
		receipt.Error = "response body read failed; exact partial bytes preserved"
		return finish(), nil
	}
	if isRedirectStatus(resp.StatusCode) {
		receipt.FailureClass, receipt.Error = "redirect_refused", "provider redirect refused; response preserved without following"
		return finish(), nil
	}
	if resp.StatusCode != http.StatusOK {
		receipt.FailureClass, receipt.Error = "http_status", fmt.Sprintf("provider returned HTTP %d", resp.StatusCode)
		return finish(), nil
	}
	result, parseErr := ApplyPolicy(p.Policy, a, native, receipt.RawResponse)
	if parseErr != nil {
		receipt.FailureClass, receipt.Error = "malformed_response", parseErr.Error()
		return finish(), nil
	}
	receipt.Status, receipt.Result = "ok", result
	return finish(), nil
}

func isTimeout(err error) bool {
	var netErr net.Error
	return errors.As(err, &netErr) && netErr.Timeout()
}

func isRedirectStatus(status int) bool {
	return status == 301 || status == 302 || status == 303 || status == 307 || status == 308
}

// ReplayLive re-derives the deterministic policy outcome from the preserved
// raw response without any network access. It verifies integrity only.
func ReplayLive(raw []byte, anchor string) (*LiveReceipt, error) {
	return replayLive(raw, anchor, LiveEndpoint)
}

func replayLive(raw []byte, anchor, endpoint string) (*LiveReceipt, error) {
	if !hashRE.MatchString(anchor) || Hash(raw) != anchor {
		return nil, fmt.Errorf("receipt anchor mismatch")
	}
	var receipt LiveReceipt
	if err := Decode(raw, &receipt); err != nil {
		return nil, err
	}
	encoded, err := JSON(&receipt)
	if err != nil || !equalJSON(encoded, raw) {
		return nil, fmt.Errorf("live receipt fields missing, null or noncanonical")
	}
	if receipt.Schema != LiveSchema || receipt.Transport != LiveTransportID || receipt.Mode != "live" ||
		receipt.ReceiptKind != "local_integrity_receipt" || receipt.ProviderAuthenticated ||
		receipt.Attempts < 0 || receipt.Attempts > 1 || receipt.LiveCalls < 0 || receipt.LiveCalls > 1 || receipt.LiveCalls > receipt.Attempts ||
		receipt.Endpoint != endpoint || receipt.Prepared == nil || receipt.RawResponse == nil || receipt.ResponseHeaders == nil ||
		receipt.CredentialSource != "env:"+LiveCredentialEnv || receipt.IdentityEvidence != liveIdentityEvidence {
		return nil, fmt.Errorf("live receipt contract mismatch")
	}
	start, startErr := time.Parse(time.RFC3339Nano, receipt.StartedAt)
	end, endErr := time.Parse(time.RFC3339Nano, receipt.CompletedAt)
	if startErr != nil || endErr != nil || end.Before(start) || receipt.LatencyMS < 0 ||
		receipt.LatencyMS != end.Sub(start).Milliseconds() || receipt.TimeoutMS < 1 || receipt.TimeoutMS > 600000 {
		return nil, fmt.Errorf("live receipt timing mismatch")
	}
	p, err := VerifyPrepared(receipt.Prepared, receipt.PreparedSHA256)
	if err != nil {
		return nil, err
	}
	r, a, native, err := ValidateRequest(p.Input)
	if err != nil {
		return nil, err
	}
	if !bytes.Equal(receipt.RequestBody, r.NativeRequest) || receipt.RequestSHA256 != Hash(r.NativeRequest) {
		return nil, fmt.Errorf("live request bytes differ from prepared native request")
	}
	if receipt.ResponseSHA256 != Hash(receipt.RawResponse) || receipt.AuthorizationHeader != "Bearer [REDACTED]" {
		return nil, fmt.Errorf("live receipt response or credential binding mismatch")
	}
	if !hashRE.MatchString(receipt.ImplementationSHA256) {
		return nil, fmt.Errorf("implementation digest invalid")
	}
	if receipt.ProvenanceNotice != p.ProvenanceNotice {
		return nil, fmt.Errorf("live receipt provenance mismatch")
	}
	if receipt.LiveCalls != map[bool]int{true: 1, false: 0}[receipt.RequestWritten] {
		return nil, fmt.Errorf("live call count does not match request-written evidence")
	}
	if receipt.HTTPStatus != 0 && (receipt.HTTPStatus < 100 || receipt.HTTPStatus > 999 || !receipt.RequestWritten) {
		return nil, fmt.Errorf("live receipt HTTP status mismatch")
	}
	if receipt.HTTPStatus == 0 && (len(receipt.ResponseHeaders) != 0 || receipt.TLS != nil) {
		return nil, fmt.Errorf("response metadata without HTTP response")
	}
	if receipt.HTTPStatus != 0 && strings.HasPrefix(endpoint, "https://") && receipt.TLS == nil {
		return nil, fmt.Errorf("HTTPS response missing TLS metadata")
	}
	for name, values := range receipt.ResponseHeaders {
		if name == "" || name != http.CanonicalHeaderKey(name) || len(values) == 0 || strings.EqualFold(name, "Set-Cookie") {
			return nil, fmt.Errorf("unsanitized response headers")
		}
	}
	if receipt.TLS != nil {
		parsed, err := url.Parse(endpoint)
		if err != nil {
			return nil, fmt.Errorf("TLS endpoint invalid")
		}
		serverName := strings.TrimRight(parsed.Hostname(), ".")
		if net.ParseIP(serverName) != nil {
			serverName = ""
		}
		if receipt.TLS.ServerName != serverName {
			return nil, fmt.Errorf("TLS server name does not match endpoint")
		}
		if receipt.TLS.Version != "TLS 1.2" && receipt.TLS.Version != "TLS 1.3" ||
			receipt.TLS.CipherSuite == "" || len(receipt.TLS.PeerCertificateSHA256) == 0 ||
			receipt.TLS.Note != "Transport metadata only; not a provider signature over the response." {
			return nil, fmt.Errorf("TLS metadata mismatch")
		}
		for _, hash := range receipt.TLS.PeerCertificateSHA256 {
			if !hashRE.MatchString(hash) {
				return nil, fmt.Errorf("TLS certificate digest invalid")
			}
		}
	}
	if err := verifyResponseCapture(&receipt); err != nil {
		return nil, err
	}
	if receipt.FailureClass == "" {
		if receipt.Status != "ok" || receipt.Error != "" || receipt.HTTPStatus != http.StatusOK ||
			receipt.ResponseCapture != "complete" || receipt.Attempts != 1 {
			return nil, fmt.Errorf("live receipt success classification mismatch")
		}
		result, err := ApplyPolicy(p.Policy, a, native, receipt.RawResponse)
		if err != nil {
			return nil, fmt.Errorf("live receipt policy replay mismatch")
		}
		want, _ := JSON(result)
		got, _ := JSON(receipt.Result)
		if !bytes.Equal(want, got) {
			return nil, fmt.Errorf("live receipt policy replay mismatch")
		}
		return &receipt, nil
	}
	if receipt.Status != "failed" || receipt.Result != nil || receipt.Error == "" {
		return nil, fmt.Errorf("live receipt failure classification mismatch")
	}
	switch receipt.FailureClass {
	case "credentials_unavailable", "credentials_invalid":
		if receipt.Attempts != 0 || receipt.RequestWritten || receipt.HTTPStatus != 0 || receipt.ResponseCapture != "not_received" {
			return nil, fmt.Errorf("credential failure cannot record a transport attempt")
		}
	case "malformed_response":
		if receipt.HTTPStatus != http.StatusOK || receipt.ResponseCapture != "complete" {
			return nil, fmt.Errorf("malformed response requires a complete HTTP 200 response")
		}
		if _, err := ApplyPolicy(p.Policy, a, native, receipt.RawResponse); err == nil || receipt.Error != err.Error() {
			return nil, fmt.Errorf("live receipt malformed classification mismatch")
		}
	case "http_status":
		if receipt.HTTPStatus == 0 || receipt.HTTPStatus == http.StatusOK || isRedirectStatus(receipt.HTTPStatus) ||
			receipt.ResponseCapture != "complete" {
			return nil, fmt.Errorf("HTTP failure classification mismatch")
		}
	case "redirect_refused":
		if !isRedirectStatus(receipt.HTTPStatus) || receipt.ResponseCapture != "complete" {
			return nil, fmt.Errorf("redirect failure classification mismatch")
		}
	case "network_error", "timeout":
		if receipt.ResponseCapture != "not_received" && receipt.ResponseCapture != "partial" {
			return nil, fmt.Errorf("network failure classification mismatch")
		}
	case "response_too_large":
		if receipt.ResponseCapture != "truncated" {
			return nil, fmt.Errorf("response limit classification mismatch")
		}
	case "credential_echo":
		if receipt.ResponseCapture != "withheld_credential" {
			return nil, fmt.Errorf("credential echo classification mismatch")
		}
	case "unsupported_response_encoding":
		if receipt.ResponseCapture != "withheld_encoding" {
			return nil, fmt.Errorf("response encoding classification mismatch")
		}
	default:
		return nil, fmt.Errorf("unknown live failure class")
	}
	if receipt.FailureClass != "credentials_unavailable" && receipt.FailureClass != "credentials_invalid" && receipt.Attempts != 1 {
		return nil, fmt.Errorf("transport failure must record one attempt")
	}
	return &receipt, nil
}

func verifyResponseCapture(r *LiveReceipt) error {
	if r.ResponseBytesObserved < 0 || r.ResponseBytesObserved > MaxLiveResponse+1 ||
		!hashRE.MatchString(r.ResponseObservedSHA256) || len(r.RawResponse) > MaxLiveResponse {
		return fmt.Errorf("response capture bounds mismatch")
	}
	if values, exists := r.ResponseHeaders["Content-Length"]; exists {
		if len(values) != 1 {
			return fmt.Errorf("ambiguous response content length")
		}
		if values[0] != "[REDACTED]" {
			length, err := strconv.ParseInt(values[0], 10, 64)
			if err != nil || length < 0 || int64(r.ResponseBytesObserved) > length ||
				r.ResponseCapture == "complete" && int64(len(r.RawResponse)) != length {
				return fmt.Errorf("response content length mismatch")
			}
		}
	}
	switch r.ResponseCapture {
	case "not_received":
		if r.HTTPStatus != 0 || r.ResponseBytesObserved != 0 || len(r.RawResponse) != 0 || r.ResponseObservedSHA256 != Hash(nil) {
			return fmt.Errorf("response recorded without HTTP response")
		}
	case "complete", "partial":
		if r.HTTPStatus == 0 || r.ResponseBytesObserved != len(r.RawResponse) || r.ResponseObservedSHA256 != Hash(r.RawResponse) {
			return fmt.Errorf("response capture bytes mismatch")
		}
	case "truncated":
		if r.HTTPStatus == 0 || r.ResponseBytesObserved != MaxLiveResponse+1 || len(r.RawResponse) != MaxLiveResponse {
			return fmt.Errorf("truncated response bounds mismatch")
		}
	case "withheld_credential", "withheld_encoding":
		if r.HTTPStatus == 0 || len(r.RawResponse) != 0 || r.ResponseCapture == "withheld_credential" && r.ResponseBytesObserved == 0 {
			return fmt.Errorf("withheld response mismatch")
		}
	default:
		return fmt.Errorf("unknown response capture state")
	}
	// A sanitized header cannot establish the original content encoding.
	for name, values := range r.ResponseHeaders {
		if strings.EqualFold(name, "Content-Encoding") {
			for _, value := range values {
				if value == "[REDACTED]" {
					return nil
				}
			}
		}
	}
	encoded := encodedResponse(r.ResponseHeaders)
	if r.ResponseCapture == "withheld_encoding" && !encoded ||
		encoded && r.ResponseCapture != "withheld_encoding" && r.ResponseCapture != "withheld_credential" {
		return fmt.Errorf("response encoding metadata mismatch")
	}
	return nil
}

func encodedResponse(headers map[string][]string) bool {
	for name, values := range headers {
		if !strings.EqualFold(name, "Content-Encoding") {
			continue
		}
		if len(values) != 1 || strings.TrimSpace(values[0]) != "" && !strings.EqualFold(strings.TrimSpace(values[0]), "identity") {
			return true
		}
	}
	return false
}

// SchemaOf returns the schema field of a receipt without trusting other fields.
func SchemaOf(raw []byte) string {
	var head struct {
		Schema string `json:"schema"`
	}
	if CheckJSON(raw) != nil || json.Unmarshal(raw, &head) != nil {
		return ""
	}
	return head.Schema
}
