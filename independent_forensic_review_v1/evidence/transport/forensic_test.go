package assessment

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"
)

func TestForensicProviderCaseAlias(t *testing.T) {
	raw, files := fixture(t)
	_, a, native, err := ValidateRequest(raw)
	if err != nil {
		t.Fatal(err)
	}
	policy, err := CompilePolicy(files)
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name string
		raw  string
	}{
		{"contradictory-noul", `{"model":"expected","answers":{"claim_0000_supported":{"noul":1,"NOUL":0},"authority_promoted":{"noul":0},"uncertainty_adequate":{"noul":1}}}`},
		{"contradictory-model", `{"model":"expected","MODEL":"different","answers":{"claim_0000_supported":{"noul":1},"authority_promoted":{"noul":0},"uncertainty_adequate":{"noul":1}}}`},
		{"uppercase-only", `{"MODEL":"different","ANSWERS":{"claim_0000_supported":{"NOUL":1},"authority_promoted":{"NOUL":0},"uncertainty_adequate":{"NOUL":1}}}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			result, err := ApplyPolicy(policy, a, native, []byte(tc.raw))
			t.Logf("raw=%s result=%+v error=%v", tc.raw, result, err)
			if err != nil {
				t.Fatal("expected to reproduce alias acceptance", err)
			}
		})
	}
}

func TestForensicOfflineMissingFields(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	r, err := EvaluateOffline(prepared, anchor, answer(t, 1, 0, 1), "mock", Hash([]byte("code")))
	if err != nil {
		t.Fatal(err)
	}
	receipt := mustJSON(t, r)
	for _, field := range []string{"live_calls", "error"} {
		t.Run(field, func(t *testing.T) {
			var obj map[string]any
			if err := json.Unmarshal(receipt, &obj); err != nil {
				t.Fatal(err)
			}
			if field == "live_calls" {
				delete(obj, field)
			} else {
				obj[field] = nil
			}
			raw := mustJSON(t, obj)
			_, err := Replay(raw, Hash(raw))
			t.Logf("field=%s replay_error=%v", field, err)
			if err != nil {
				t.Fatal("expected to reproduce permissive offline replay", err)
			}
		})
	}
}

func TestForensicReplayContradictoryWireMetadata(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
		_, _ = w.Write(answer(t, 1, 0, 1))
	})
	r, err := EvaluateLive(prepared, anchor, Hash([]byte("code")), testTransport(srv, testKey, time.Second))
	if err != nil || r.Status != "ok" {
		t.Fatal(err, r.Status)
	}
	r.ResponseHeaders["Content-Length"] = []string{"0"}
	r.TLS.ServerName = "not-the-recorded-endpoint.invalid"
	raw := mustJSON(t, r)
	_, err = replayLive(raw, Hash(raw), r.Endpoint)
	t.Logf("complete_body_bytes=%d content_length=%s tls_name=%s replay_error=%v",
		len(r.RawResponse), r.ResponseHeaders["Content-Length"], r.TLS.ServerName, err)
	if err != nil {
		t.Fatal("expected to reproduce metadata acceptance", err)
	}
}

func TestForensicRepeatedPreparedAttempt(t *testing.T) {
	prepared, anchor, _ := preparedFixture(t)
	c := &captured{}
	srv := liveServer(t, c, func(w http.ResponseWriter, _ *http.Request, _ []byte) {
		_, _ = w.Write(answer(t, 1, 0, 1))
	})
	for i := 0; i < 2; i++ {
		r, err := EvaluateLive(prepared, anchor, Hash([]byte("code")), testTransport(srv, testKey, time.Second))
		if err != nil || r.Status != "ok" {
			t.Fatal(err, r.Status)
		}
		t.Logf("evaluation=%d same_prepared=%s attempts=%d live_calls=%d", i+1, r.PreparedSHA256, r.Attempts, r.LiveCalls)
	}
	if c.count.Load() != 2 {
		t.Fatal("expected two independent explicitly invoked loopback calls")
	}
}
