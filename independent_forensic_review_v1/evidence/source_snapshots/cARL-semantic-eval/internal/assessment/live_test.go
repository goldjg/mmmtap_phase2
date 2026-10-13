package assessment

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// No test may reach the production SystemOne endpoint: the command-level
// credential source is blanked for the whole package test run.
func TestMain(m *testing.M) {
	liveCredential = func() string { return "" }
	os.Exit(m.Run())
}

const testKey = "test-key-not-a-credential-7f3a"

type captured struct {
	mu      sync.Mutex
	count   atomic.Int32
	bodies  [][]byte
	headers []http.Header
}

func (c *captured) record(r *http.Request) []byte {
	body, _ := io.ReadAll(r.Body)
	c.count.Add(1)
	c.mu.Lock()
	defer c.mu.Unlock()
	c.bodies = append(c.bodies, body)
	c.headers = append(c.headers, r.Header.Clone())
	return body
}

func testTransport(srv *httptest.Server, key string, timeout time.Duration) *LiveTransport {
	base := srv.Client().Transport.(*http.Transport).Clone()
	return &LiveTransport{endpoint: srv.URL + "/v1/systemone", key: key, timeout: timeout, client: newClient(base), now: time.Now}
}

func preparedFixture(t *testing.T) ([]byte, string, *Request) {
	t.Helper()
	raw, files := fixture(t)
	var request Request
	if err := Decode(raw, &request); err != nil {
		t.Fatal(err)
	}
	var native bytes.Buffer
	native.WriteString(" \n")
	if err := json.Indent(&native, request.NativeRequest, "", "  "); err != nil {
		t.Fatal(err)
	}
	native.WriteString("\n\t")
	request.NativeRequest = native.Bytes()
	raw = mustJSON(t, &request)
	p, err := Prepare(raw, files, Hash([]byte("live-test-implementation")))
	if err != nil {
		t.Fatal(err)
	}
	prepared := mustJSON(t, p)
	r, _, _, err := ValidateRequest(p.Input)
	if err != nil {
		t.Fatal(err)
	}
	return prepared, Hash(prepared), r
}

func liveServer(t *testing.T, c *captured, handler func(http.ResponseWriter, *http.Request, []byte)) *httptest.Server {
	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/systemone" {
			t.Errorf("unexpected follow-up request to %s", r.URL.Path)
			w.WriteHeader(http.StatusTeapot)
			return
		}
		handler(w, r, c.record(r))
	}))
	t.Cleanup(srv.Close)
	return srv
}

func TestLiveSingleAttemptExactBytesAndReplay(t *testing.T) {
	prepared, anchor, request := preparedFixture(t)
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
		w.Header().Set("X-Request-Id", "fixture-request")
		w.Header().Set("Set-Cookie", "session=secret")
		_, _ = w.Write(answer(t, 0.2, 0.1, 0.9))
	})
	code := Hash([]byte("live-test-implementation"))
	r, err := EvaluateLive(prepared, anchor, code, testTransport(srv, testKey, 5*time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if c.count.Load() != 1 || !bytes.Equal(c.bodies[0], request.NativeRequest) {
		t.Fatal("live transport did not send the exact prepared native request once")
	}
	if c.headers[0].Get("Authorization") != "Bearer "+testKey || c.headers[0].Get("Content-Type") != "application/json" {
		t.Fatal("wire contract differs from native JEV")
	}
	if c.headers[0].Get("Accept-Encoding") != "identity" || r.ResponseCapture != "complete" ||
		!bytes.Equal(r.RawResponse, answer(t, 0.2, 0.1, 0.9)) || r.ResponseObservedSHA256 != r.ResponseSHA256 ||
		r.ResponseBytesObserved != len(r.RawResponse) {
		t.Fatal("response bytes or encoding changed silently")
	}
	if r.Status != "ok" || r.Result == nil || r.LiveCalls != 1 || r.Attempts != 1 || !r.RequestWritten ||
		r.ReceiptKind != "local_integrity_receipt" || r.ProviderAuthenticated || r.TLS == nil ||
		len(r.TLS.PeerCertificateSHA256) == 0 || r.Result.Disposition != "challenge_required" {
		t.Fatalf("unexpected receipt: %+v", r)
	}
	if _, ok := r.ResponseHeaders["Set-Cookie"]; ok {
		t.Fatal("cookie preserved")
	}
	receipt := mustJSON(t, r)
	if bytes.Contains(receipt, []byte(testKey)) {
		t.Fatal("credential leaked into receipt")
	}
	if _, err := replayLive(receipt, Hash(receipt), r.Endpoint); err != nil {
		t.Fatal(err)
	}
	if _, err := ReplayLive(receipt, Hash(receipt)); err == nil {
		t.Fatal("test endpoint receipt accepted as production receipt")
	}
	if SchemaOf(receipt) != LiveSchema {
		t.Fatal("schema dispatch")
	}
	mutations := map[string]func(*LiveReceipt){
		"disposition":       func(x *LiveReceipt) { x.Result.Disposition = "no_challenge" },
		"response":          func(x *LiveReceipt) { x.RawResponse = answer(t, 1, 0, 1) },
		"response-hash":     func(x *LiveReceipt) { x.RawResponse = answer(t, 1, 0, 1); x.ResponseSHA256 = Hash(x.RawResponse) },
		"request":           func(x *LiveReceipt) { x.RequestBody = append([]byte(nil), '{', '}') },
		"provider-auth":     func(x *LiveReceipt) { x.ProviderAuthenticated = true },
		"calls":             func(x *LiveReceipt) { x.LiveCalls = 2 },
		"attempts":          func(x *LiveReceipt) { x.Attempts = 2 },
		"written":           func(x *LiveReceipt) { x.RequestWritten = false },
		"kind":              func(x *LiveReceipt) { x.ReceiptKind = "provider_authenticated_receipt" },
		"credential":        func(x *LiveReceipt) { x.AuthorizationHeader = "Bearer " + testKey },
		"impl":              func(x *LiveReceipt) { x.ImplementationSHA256 = "unknown" },
		"failed-ok":         func(x *LiveReceipt) { x.Status = "failed" },
		"negative-attempts": func(x *LiveReceipt) { x.Attempts = -1 },
		"credential-source": func(x *LiveReceipt) { x.CredentialSource = "config:file" },
		"identity-evidence": func(x *LiveReceipt) { x.IdentityEvidence = "attested" },
		"provenance":        func(x *LiveReceipt) { x.ProvenanceNotice = "authenticated" },
		"start-time":        func(x *LiveReceipt) { x.StartedAt = "invalid" },
		"end-time":          func(x *LiveReceipt) { x.CompletedAt = "invalid" },
		"latency":           func(x *LiveReceipt) { x.LatencyMS = -1 },
		"timeout":           func(x *LiveReceipt) { x.TimeoutMS = 0 },
		"oversized-timeout": func(x *LiveReceipt) { x.TimeoutMS = 600001 },
		"success-error":     func(x *LiveReceipt) { x.Error = "not successful" },
		"capture":           func(x *LiveReceipt) { x.ResponseCapture = "redacted" },
		"observed-bytes":    func(x *LiveReceipt) { x.ResponseBytesObserved++ },
		"observed-hash":     func(x *LiveReceipt) { x.ResponseObservedSHA256 = Hash([]byte("other")) },
		"missing-tls":       func(x *LiveReceipt) { x.TLS = nil },
		"tls-version":       func(x *LiveReceipt) { x.TLS.Version = "TLS 1.0" },
		"tls-hash":          func(x *LiveReceipt) { x.TLS.PeerCertificateSHA256[0] = "wrong" },
		"old-draft-schema":  func(x *LiveReceipt) { x.Schema = Version + "-live-receipt" },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			var copy LiveReceipt
			if err := json.Unmarshal(receipt, &copy); err != nil {
				t.Fatal(err)
			}
			mutate(&copy)
			tampered := mustJSON(t, &copy)
			if _, err := replayLive(tampered, Hash(tampered), r.Endpoint); err == nil {
				t.Fatalf("tamper %s not detected", name)
			}
		})
	}
	if _, err := replayLive(receipt, Hash([]byte("other")), r.Endpoint); err == nil {
		t.Fatal("external anchor not enforced")
	}
	if c.count.Load() != 1 {
		t.Fatal("replay touched the network")
	}
}

func TestLiveFailuresAreSingleFirstAttempts(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	code := Hash([]byte("live-test-implementation"))
	cases := []struct {
		name, class string
		status      int
		timeout     time.Duration
		handler     func(http.ResponseWriter, *http.Request, []byte)
	}{
		{"http401", "http_status", 401, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(401) }},
		{"http403", "http_status", 403, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(403) }},
		{"http503", "http_status", 503, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(503) }},
		{"http500", "http_status", 500, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			w.WriteHeader(500)
			_, _ = w.Write([]byte(`{"error":"fixture"}`))
		}},
		{"http429", "http_status", 429, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			w.Header().Set("Retry-After", "0")
			w.WriteHeader(429)
		}},
		{"malformed", "malformed_response", 200, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			_, _ = w.Write([]byte(`{"model":"fixture","answers":{}}`))
		}},
		{"truncated-json", "malformed_response", 200, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			_, _ = w.Write([]byte(`{`))
		}},
		{"redirect302", "redirect_refused", 302, time.Second, func(w http.ResponseWriter, r *http.Request, _ []byte) {
			http.Redirect(w, r, "/elsewhere", http.StatusFound)
			_, _ = w.Write([]byte("redirect /elsewhere"))
		}},
		{"redirect307", "redirect_refused", 307, time.Second, func(w http.ResponseWriter, r *http.Request, _ []byte) {
			http.Redirect(w, r, "/elsewhere", http.StatusTemporaryRedirect)
			_, _ = w.Write([]byte("redirect /elsewhere"))
		}},
		{"redirect308", "redirect_refused", 308, time.Second, func(w http.ResponseWriter, r *http.Request, _ []byte) {
			http.Redirect(w, r, "/elsewhere", http.StatusPermanentRedirect)
			_, _ = w.Write([]byte("redirect /elsewhere"))
		}},
		{"body-disconnect", "network_error", 200, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			w.Header().Set("Content-Length", "100")
			_, _ = w.Write([]byte("short"))
		}},
		{"body-timeout", "timeout", 200, 150 * time.Millisecond, func(w http.ResponseWriter, r *http.Request, _ []byte) {
			_, _ = w.Write([]byte("prefix"))
			w.(http.Flusher).Flush()
			<-r.Context().Done()
		}},
		{"oversized", "response_too_large", 200, 5 * time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			_, _ = w.Write(bytes.Repeat([]byte("a"), MaxLiveResponse+16))
		}},
		{"timeout", "timeout", 0, 150 * time.Millisecond, func(_ http.ResponseWriter, r *http.Request, _ []byte) {
			select {
			case <-r.Context().Done():
			case <-time.After(5 * time.Second):
			}
		}},
		{"echoed-key", "credential_echo", 200, time.Second, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
			w.Header().Set("X-Echo", "Bearer "+testKey)
			_, _ = w.Write([]byte(`{"echo":"` + testKey + `"}`))
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			c := &captured{}
			srv := liveServer(t, c, tc.handler)
			r, err := EvaluateLive(prepared, anchor, code, testTransport(srv, testKey, tc.timeout))
			if err != nil {
				t.Fatal(err)
			}
			if c.count.Load() != 1 {
				t.Fatalf("expected exactly one request, got %d", c.count.Load())
			}
			if r.Status != "failed" || r.FailureClass != tc.class || r.Result != nil || r.Attempts != 1 ||
				r.LiveCalls != 1 || !r.RequestWritten || r.HTTPStatus != tc.status {
				t.Fatalf("unexpected receipt: status=%s class=%s http=%d calls=%d err=%s",
					r.Status, r.FailureClass, r.HTTPStatus, r.LiveCalls, r.Error)
			}
			receipt := mustJSON(t, r)
			if bytes.Contains(receipt, []byte(testKey)) {
				t.Fatal("credential leaked into failed receipt")
			}
			if _, err := replayLive(receipt, Hash(receipt), r.Endpoint); err != nil {
				t.Fatal(err)
			}
			if tc.name == "oversized" && len(r.RawResponse) != MaxLiveResponse {
				t.Fatal("oversized prefix not preserved")
			}
			if tc.class == "redirect_refused" && (!bytes.Contains(r.RawResponse, []byte("/elsewhere")) || r.ResponseCapture != "complete") {
				t.Fatal("redirect response body was discarded")
			}
			if tc.name == "body-disconnect" && (!bytes.Equal(r.RawResponse, []byte("short")) || r.ResponseCapture != "partial") {
				t.Fatal("partial response bytes were not preserved")
			}
		})
	}
}

func TestLiveWithoutCredentialOrReachableProviderMakesNoCall(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	code := Hash([]byte("live-test-implementation"))
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(200) })
	for _, key := range []string{"", "   ", "bad\nkey", " key", "key ", "bad\tkey", "bad\x7fkey", "badékey", "bad=padding"} {
		r, err := EvaluateLive(prepared, anchor, code, testTransport(srv, key, time.Second))
		if err != nil {
			t.Fatal(err)
		}
		class := "credentials_invalid"
		if strings.TrimSpace(key) == "" {
			class = "credentials_unavailable"
		}
		if r.FailureClass != class || r.Attempts != 0 || r.LiveCalls != 0 || r.RequestWritten {
			t.Fatal("credential failure recorded as a call")
		}
		raw := mustJSON(t, r)
		if _, err := replayLive(raw, Hash(raw), r.Endpoint); err != nil {
			t.Fatal(err)
		}
	}
	if c.count.Load() != 0 {
		t.Fatal("request sent without credentials")
	}
	if _, err := EvaluateLive(prepared, Hash([]byte("wrong")), code, testTransport(srv, testKey, time.Second)); err == nil {
		t.Fatal("unanchored prepared artifact accepted")
	}
	if _, err := EvaluateLive(prepared, anchor, "not-a-digest", testTransport(srv, testKey, time.Second)); err == nil {
		t.Fatal("missing implementation digest accepted")
	}
	if _, err := EvaluateLive(prepared, anchor, code, testTransport(srv, testKey, 0)); err == nil {
		t.Fatal("unbounded timeout accepted")
	}
	if c.count.Load() != 0 {
		t.Fatal("request sent for a rejected preparation")
	}
	closed := httptest.NewTLSServer(http.NotFoundHandler())
	tr := testTransport(closed, testKey, time.Second)
	closed.Close()
	r, err := EvaluateLive(prepared, anchor, code, tr)
	if err != nil {
		t.Fatal(err)
	}
	if r.FailureClass != "network_error" || r.LiveCalls != 0 || r.RequestWritten || r.Attempts != 1 {
		t.Fatalf("unreachable provider misclassified: %+v", r)
	}
	if strings.Contains(r.Error, testKey) {
		t.Fatal("credential in error")
	}
}

func TestLiveResponseCaptureNeverClaimsRedactedBytesAreOriginal(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	code := Hash([]byte("live-test-implementation"))
	escaped := ""
	for _, c := range testKey {
		escaped += fmt.Sprintf("\\u%04x", c)
	}
	for name, model := range map[string]string{"literal-key": testKey, "json-escaped-key": escaped, "not-a-secret": "fixture-model-not-live"} {
		t.Run(name, func(t *testing.T) {
			wire := bytes.ReplaceAll(answer(t, 1, 0, 1), []byte("fixture-model-not-live"), []byte(model))
			c := &captured{}
			srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
				w.Header().Set("X-Echo", testKey)
				w.Header().Set("X-"+testKey, "secret-bearing header name")
				_, _ = w.Write(wire)
			})
			r, err := EvaluateLive(prepared, anchor, code, testTransport(srv, testKey, time.Second))
			if err != nil {
				t.Fatal(err)
			}
			if r.ResponseBytesObserved != len(wire) || r.ResponseObservedSHA256 != Hash(wire) || c.count.Load() != 1 {
				t.Fatal("observed-byte evidence lost")
			}
			if name == "not-a-secret" {
				if r.Status != "ok" || r.ResponseCapture != "complete" || !bytes.Equal(r.RawResponse, wire) {
					t.Fatal("safe response was changed")
				}
			} else if r.Status != "failed" || r.FailureClass != "credential_echo" || r.Result != nil ||
				r.ResponseCapture != "withheld_credential" || len(r.RawResponse) != 0 || r.ResponseSHA256 != Hash(nil) {
				t.Fatal("credential echo silently redacted into apparently original response")
			}
			raw := mustJSON(t, r)
			if strings.Contains(strings.ToLower(string(raw)), strings.ToLower(testKey)) {
				t.Fatal("secret-bearing header or result leaked")
			}
			if _, err := replayLive(raw, Hash(raw), r.Endpoint); err != nil {
				t.Fatal(err)
			}
			if r.FailureClass == "credential_echo" {
				r.ResponseCapture = "complete"
				tampered := mustJSON(t, r)
				if _, err := replayLive(tampered, Hash(tampered), r.Endpoint); err == nil {
					t.Fatal("withheld response accepted as original")
				}
			}
		})
	}
}

func TestLiveEncodedResponseIsNotSilentlyDecompressed(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	var wire bytes.Buffer
	zw := gzip.NewWriter(&wire)
	if _, err := zw.Write(answer(t, 1, 0, 1)); err != nil {
		t.Fatal(err)
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
		w.Header().Set("Content-Encoding", "gzip")
		_, _ = w.Write(wire.Bytes())
	})
	r, err := EvaluateLive(prepared, anchor, Hash([]byte("code")), testTransport(srv, testKey, time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if r.FailureClass != "unsupported_response_encoding" || r.ResponseCapture != "withheld_encoding" ||
		len(r.RawResponse) != 0 || r.ResponseObservedSHA256 != Hash(wire.Bytes()) || r.ResponseBytesObserved != wire.Len() ||
		c.count.Load() != 1 || c.headers[0].Get("Accept-Encoding") != "identity" {
		t.Fatal("compressed bytes silently replaced by decompressed bytes")
	}
	raw := mustJSON(t, r)
	if _, err := replayLive(raw, Hash(raw), r.Endpoint); err != nil {
		t.Fatal(err)
	}
}

func TestLiveReplayRejectsMissingNullAndContradictoryFailureFields(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	r, err := EvaluateLive(prepared, anchor, Hash([]byte("code")), NewLiveTransport("", time.Second))
	if err != nil {
		t.Fatal(err)
	}
	raw := mustJSON(t, r)
	for _, field := range []string{"attempts", "live_calls", "request_written", "provider_authenticated", "response_capture",
		"response_bytes_observed", "response_observed_sha256", "timeout_ms", "started_at", "completed_at", "latency_ms", "result", "tls"} {
		for _, operation := range []string{"missing", "null"} {
			if operation == "null" && (field == "result" || field == "tls") {
				continue
			}
			t.Run(field+"/"+operation, func(t *testing.T) {
				var object map[string]any
				if err := json.Unmarshal(raw, &object); err != nil {
					t.Fatal(err)
				}
				if operation == "missing" {
					delete(object, field)
				} else {
					object[field] = nil
				}
				tampered := mustJSON(t, object)
				if _, err := ReplayLive(tampered, Hash(tampered)); err == nil {
					t.Fatal("missing/null field accepted")
				}
			})
		}
	}
	mutations := map[string]func(*LiveReceipt){
		"negative-attempts":          func(x *LiveReceipt) { x.Attempts = -1 },
		"negative-calls":             func(x *LiveReceipt) { x.LiveCalls = -1 },
		"attempt-without-credential": func(x *LiveReceipt) { x.Attempts = 1 },
		"unknown-failure":            func(x *LiveReceipt) { x.FailureClass = "anything" },
		"http-without-response":      func(x *LiveReceipt) { x.FailureClass = "http_status"; x.Attempts = 1 },
		"redirect-without-response":  func(x *LiveReceipt) { x.FailureClass = "redirect_refused"; x.Attempts = 1 },
		"malformed-without-response": func(x *LiveReceipt) { x.FailureClass = "malformed_response"; x.Attempts = 1 },
		"failure-without-error":      func(x *LiveReceipt) { x.Error = "" },
		"error-with-success":         func(x *LiveReceipt) { x.Status = "ok" },
		"headers-without-response":   func(x *LiveReceipt) { x.ResponseHeaders["X-Test"] = []string{"test"} },
		"response-without-attempt":   func(x *LiveReceipt) { x.HTTPStatus = 200 },
		"false-complete":             func(x *LiveReceipt) { x.ResponseCapture = "complete" },
		"false-truncated":            func(x *LiveReceipt) { x.ResponseCapture = "truncated" },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			var copy LiveReceipt
			if err := json.Unmarshal(raw, &copy); err != nil {
				t.Fatal(err)
			}
			mutate(&copy)
			tampered := mustJSON(t, &copy)
			if _, err := ReplayLive(tampered, Hash(tampered)); err == nil {
				t.Fatal("contradictory failure accepted")
			}
		})
	}
}

func TestLiveCredentialInPreparedInputIsNotCopiedOrSent(t *testing.T) {
	raw, files := fixture(t)
	var request Request
	if err := Decode(raw, &request); err != nil {
		t.Fatal(err)
	}
	var native NativeRequest
	if err := Decode(request.NativeRequest, &native); err != nil {
		t.Fatal(err)
	}
	native.Model = testKey
	request.NativeRequest = mustJSON(t, native)
	p, err := Prepare(mustJSON(t, request), files, Hash([]byte("code")))
	if err != nil {
		t.Fatal(err)
	}
	prepared := mustJSON(t, p)
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(200) })
	if _, err := EvaluateLive(prepared, Hash(prepared), Hash([]byte("code")), testTransport(srv, testKey, time.Second)); err == nil {
		t.Fatal("credential-bearing input was sent")
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "prepared.json")
	if err := WriteNew(path, prepared); err != nil {
		t.Fatal(err)
	}
	oldCredential, oldTransport := liveCredential, liveTransport
	t.Cleanup(func() { liveCredential, liveTransport = oldCredential, oldTransport })
	liveCredential = func() string { return testKey }
	liveTransport = func(key string, timeout time.Duration) *LiveTransport { return testTransport(srv, key, timeout) }
	dest := filepath.Join(dir, "attempt")
	var log bytes.Buffer
	if err := Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", Hash(prepared), "--authorize-live",
		"--timeout-seconds", "1", "--out", dest}, &log, &log, Hash([]byte("code"))); err == nil {
		t.Fatal("credential-bearing input was persisted")
	}
	if _, err := os.Stat(filepath.Join(dest, "prepared.json")); !os.IsNotExist(err) {
		t.Fatal("credential-bearing prepared input copied")
	}
	if c.count.Load() != 0 {
		t.Fatal("credential-bearing input reached transport")
	}
}

func TestProductionTransportIsFixed(t *testing.T) {
	tr := NewLiveTransport(testKey, time.Second)
	if tr.endpoint != LiveEndpoint {
		t.Fatal("production endpoint not fixed")
	}
	h := tr.client.Transport.(*http.Transport)
	if h.Proxy != nil || !h.DisableKeepAlives || !h.DisableCompression || h.ForceAttemptHTTP2 ||
		h.TLSClientConfig.MinVersion < 0x0303 || h.TLSClientConfig.InsecureSkipVerify || tr.client.CheckRedirect == nil {
		t.Fatal("production transport hardening missing")
	}
}

func TestLiveRejectsUntrustedTLSBeforeWritingRequest(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) { w.WriteHeader(200) })
	tr := testTransport(srv, testKey, time.Second)
	tr.client = newClient(&http.Transport{})
	r, err := EvaluateLive(prepared, anchor, Hash([]byte("code")), tr)
	if err != nil {
		t.Fatal(err)
	}
	if r.FailureClass != "network_error" || r.Attempts != 1 || r.RequestWritten || r.LiveCalls != 0 || c.count.Load() != 0 {
		t.Fatal("untrusted TLS connection received a request")
	}
	raw := mustJSON(t, r)
	if _, err := replayLive(raw, Hash(raw), r.Endpoint); err != nil {
		t.Fatal(err)
	}
}

func TestCLIEvaluateLiveRequiresAuthorisationAndPreservesFailure(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	root := t.TempDir()
	path := filepath.Join(root, "prepared.json")
	if err := WriteNew(path, prepared); err != nil {
		t.Fatal(err)
	}
	code := Hash([]byte("live-test-implementation"))
	var log bytes.Buffer
	unauthorised := filepath.Join(root, "unauthorised")
	if err := Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor, "--timeout-seconds", "5", "--out", unauthorised}, &log, &log, code); err == nil {
		t.Fatal("live evaluation without explicit authorisation")
	}
	if _, err := os.Stat(unauthorised); !os.IsNotExist(err) {
		t.Fatal("unauthorised call reserved an attempt")
	}
	if err := Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor, "--authorize-live", "--timeout-seconds", "0", "--out", unauthorised}, &log, &log, code); err == nil {
		t.Fatal("unbounded timeout accepted")
	}
	// Production transport with a blank credential: no network activity is possible.
	out := filepath.Join(root, "attempt")
	args := []string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor, "--authorize-live", "--timeout-seconds", "5", "--out", out}
	if err := Run(args, &log, &log, code); err == nil || !strings.Contains(err.Error(), "credentials_unavailable") {
		t.Fatalf("credential failure not surfaced: %v", err)
	}
	receipt, err := Read(filepath.Join(out, "live_receipt.json"))
	if err != nil {
		t.Fatal(err)
	}
	intent, err := Read(filepath.Join(out, "intent.json"))
	if err != nil || !bytes.Contains(intent, []byte("single_first_attempt_no_retry")) {
		t.Fatal("intent not recorded before evaluation")
	}
	if err := Run(args, &log, &log, code); err == nil {
		t.Fatal("first attempt overwritten")
	}
	again, _ := Read(filepath.Join(out, "live_receipt.json"))
	if !bytes.Equal(receipt, again) {
		t.Fatal("first attempt changed")
	}
	log.Reset()
	if err := Run([]string{"replay", "--receipt", filepath.Join(out, "live_receipt.json"), "--receipt-sha256", Hash(receipt)}, &log, &log, code); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(log.String(), "recorded_live_calls=0") {
		t.Fatal(log.String())
	}

	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) { _, _ = w.Write(answer(t, 1, 0, 1)) })
	defer func(previousTransport func(string, time.Duration) *LiveTransport, previousCredential func() string) {
		liveTransport, liveCredential = previousTransport, previousCredential
	}(liveTransport, liveCredential)
	liveTransport = func(key string, timeout time.Duration) *LiveTransport { return testTransport(srv, key, timeout) }
	liveCredential = func() string { return testKey }
	ok := filepath.Join(root, "ok")
	if err := Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor, "--authorize-live", "--timeout-seconds", "5", "--out", ok}, &log, &log, code); err != nil {
		t.Fatal(err)
	}
	okReceipt, err := Read(filepath.Join(ok, "live_receipt.json"))
	if err != nil || c.count.Load() != 1 || bytes.Contains(okReceipt, []byte(testKey)) {
		t.Fatal("successful live receipt not persisted safely")
	}
	if err := Run([]string{"replay", "--receipt", filepath.Join(ok, "live_receipt.json"), "--receipt-sha256", Hash(okReceipt)}, &log, &log, code); err == nil {
		t.Fatal("non-production endpoint receipt replayed as production")
	}
	call, err := Read(filepath.Join(ok, "live_call.json"))
	if err != nil || !bytes.Contains(call, []byte(`"live_calls":1`)) {
		t.Fatal("live call record missing")
	}

	// A truncated response still leaves the call and exact response prefix on disk.
	big := liveServer(t, &captured{}, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
		_, _ = w.Write(bytes.Repeat([]byte("b"), MaxLiveResponse+1))
	})
	liveTransport = func(key string, timeout time.Duration) *LiveTransport { return testTransport(big, key, timeout) }
	large := filepath.Join(root, "large")
	if err := Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor, "--authorize-live", "--timeout-seconds", "5", "--out", large}, &log, &log, code); err == nil {
		t.Fatal("oversized response accepted")
	}
	call, err = Read(filepath.Join(large, "live_call.json"))
	if err != nil || !bytes.Contains(call, []byte(`"response_too_large"`)) || !bytes.Contains(call, []byte(`"live_calls":1`)) {
		t.Fatal("oversized live call not evidenced", err)
	}
	if info, err := os.Stat(filepath.Join(large, "response.bin")); err != nil || info.Size() != MaxLiveResponse {
		t.Fatal("oversized raw prefix not preserved", err)
	}

	input, files := fixture(t)
	files[".github/instructions/research/unused.instructions.md"] = []byte("<!-- version: 1.0.0 -->\n# Unselected\n" + strings.Repeat(" ", (2<<20)-8192))
	p, err := Prepare(input, files, code)
	if err != nil {
		t.Fatal(err)
	}
	largePrepared := mustJSON(t, p)
	largePath := filepath.Join(root, "large-prepared.json")
	if err := WriteNew(largePath, largePrepared); err != nil {
		t.Fatal(err)
	}
	capacity := filepath.Join(root, "capacity")
	err = Run([]string{"evaluate-live", "--prepared", largePath, "--prepared-sha256", Hash(largePrepared),
		"--authorize-live", "--timeout-seconds", "5", "--out", capacity}, &log, &log, code)
	if err == nil || !strings.Contains(err.Error(), "serialized artifact exceeds replay capacity") {
		t.Fatalf("expected receipt capacity failure, got %v", err)
	}
	if _, err := Read(filepath.Join(capacity, "live_call.json")); err != nil {
		t.Fatal("call missing after receipt capacity failure", err)
	}
	if info, err := os.Stat(filepath.Join(capacity, "response.bin")); err != nil || info.Size() != MaxLiveResponse {
		t.Fatal("body missing after receipt capacity failure", err)
	}
	if _, err := Read(filepath.Join(capacity, "failure.json")); err != nil {
		t.Fatal("capacity failure not persisted", err)
	}

	blocked := filepath.Join(root, "blocked-response-write")
	liveTransport = func(key string, timeout time.Duration) *LiveTransport {
		if err := WriteNew(filepath.Join(blocked, "response.bin"), []byte("existing")); err != nil {
			t.Fatal(err)
		}
		return testTransport(srv, key, timeout)
	}
	err = Run([]string{"evaluate-live", "--prepared", path, "--prepared-sha256", anchor,
		"--authorize-live", "--timeout-seconds", "5", "--out", blocked}, &log, &log, code)
	if err == nil {
		t.Fatal("response write collision ignored")
	}
	if _, err := Read(filepath.Join(blocked, "live_call.json")); err != nil {
		t.Fatal("call evidence lost after body write failure", err)
	}
	unchanged, _ := Read(filepath.Join(blocked, "response.bin"))
	if string(unchanged) != "existing" {
		t.Fatal("exclusive body write overwrote evidence")
	}
}
