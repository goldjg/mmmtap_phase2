package assessment

import "fmt"

type Prepared struct {
	Schema               string            `json:"schema"`
	Input                []byte            `json:"input"`
	PolicyFiles          map[string][]byte `json:"policy_files"`
	Policy               *Policy           `json:"policy"`
	Bindings             map[string]string `json:"bindings"`
	ImplementationSHA256 string            `json:"implementation_sha256"`
	ProvenanceNotice     string            `json:"provenance_notice"`
}

func Prepare(input []byte, files map[string][]byte, implementation string) (*Prepared, error) {
	r, _, _, err := ValidateRequest(input)
	if err != nil {
		return nil, err
	}
	if !hashRE.MatchString(implementation) {
		return nil, fmt.Errorf("implementation digest required")
	}
	policy, err := CompilePolicy(files)
	if err != nil {
		return nil, err
	}
	policyJSON, err := JSON(policy)
	if err != nil {
		return nil, err
	}
	snapshotJSON, err := JSON(files)
	if err != nil {
		return nil, err
	}
	return &Prepared{
		Schema: Version + "-prepared", Input: input, PolicyFiles: files, Policy: policy,
		ImplementationSHA256: implementation,
		ProvenanceNotice:     "Supplied evidence: source/manifest/parent byte bindings verified; archive not reopened by cARL; no Git, deployment, publisher or provider authentication asserted.",
		Bindings: map[string]string{
			"input": Hash(input), "native_request": Hash(r.NativeRequest),
			"source": r.Source.SHA256, "source_manifest": r.Source.ManifestSHA256,
			"parent_checkpoint": r.ParentSHA256, "assessment": Hash(r.Assessment),
			"policy_snapshot": Hash(snapshotJSON), "compiled_policy": Hash(policyJSON),
		},
	}, nil
}

func VerifyPrepared(raw []byte, expected string) (*Prepared, error) {
	if !hashRE.MatchString(expected) || Hash(raw) != expected {
		return nil, fmt.Errorf("prepared anchor mismatch")
	}
	var p Prepared
	if err := Decode(raw, &p); err != nil {
		return nil, err
	}
	recomputed, err := Prepare(p.Input, p.PolicyFiles, p.ImplementationSHA256)
	if err != nil {
		return nil, err
	}
	want, err := JSON(recomputed)
	if err != nil {
		return nil, err
	}
	if !equalJSON(want, raw) {
		return nil, fmt.Errorf("prepared replay mismatch")
	}
	return &p, nil
}

type Receipt struct {
	Schema               string    `json:"schema"`
	Mode                 string    `json:"mode"`
	Status               string    `json:"status"`
	Error                string    `json:"error,omitempty"`
	Prepared             []byte    `json:"prepared"`
	PreparedSHA256       string    `json:"prepared_sha256"`
	RawResponse          []byte    `json:"raw_response"`
	ResponseSHA256       string    `json:"response_sha256"`
	Result               *Decision `json:"result"`
	ImplementationSHA256 string    `json:"implementation_sha256"`
	LiveCalls            int       `json:"live_calls"`
	IdentityEvidence     string    `json:"identity_evidence"`
}

func EvaluateOffline(prepared []byte, anchor string, response []byte, mode, implementation string) (*Receipt, error) {
	if mode != "mock" && mode != "imported_unverified" {
		return nil, fmt.Errorf("only mock or imported_unverified evidence is allowed")
	}
	if !hashRE.MatchString(implementation) {
		return nil, fmt.Errorf("implementation digest required")
	}
	p, err := VerifyPrepared(prepared, anchor)
	if err != nil {
		return nil, err
	}
	_, a, native, err := ValidateRequest(p.Input)
	if err != nil {
		return nil, err
	}
	result, parseErr := ApplyPolicy(p.Policy, a, native, response)
	status := "mock_ok"
	if mode == "imported_unverified" {
		status = "imported_unverified"
	}
	receipt := &Receipt{Schema: Version + "-receipt", Mode: mode, Status: status,
		Prepared: prepared, PreparedSHA256: anchor, RawResponse: response,
		ResponseSHA256: Hash(response), Result: result, ImplementationSHA256: implementation,
		IdentityEvidence: "unverified_response_field_not_provider_attestation"}
	if parseErr != nil {
		receipt.Status = "failed"
		receipt.Error = parseErr.Error()
	}
	return receipt, nil
}

// Replay requires an independently retained digest. A self-consistent hash is
// integrity evidence only, never a signature or proof of a provider invocation.
func Replay(raw []byte, anchor string) (*Receipt, error) {
	if !hashRE.MatchString(anchor) || Hash(raw) != anchor {
		return nil, fmt.Errorf("receipt anchor mismatch")
	}
	var receipt Receipt
	if err := Decode(raw, &receipt); err != nil {
		return nil, err
	}
	replayed, err := EvaluateOffline(receipt.Prepared, receipt.PreparedSHA256,
		receipt.RawResponse, receipt.Mode, receipt.ImplementationSHA256)
	if err != nil {
		return nil, err
	}
	want, err := JSON(replayed)
	if err != nil {
		return nil, err
	}
	if !equalJSON(want, raw) {
		return nil, fmt.Errorf("receipt policy replay mismatch")
	}
	return replayed, nil
}
