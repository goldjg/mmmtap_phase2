package assessment

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/fs"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/goldjg/carl/internal/pack"
)

type Rule struct {
	ID        string  `json:"id"`
	Signal    string  `json:"signal"`
	Operator  string  `json:"operator"`
	Threshold float64 `json:"threshold"`
	Action    string  `json:"action"`
}

type BoundRule struct {
	Pack       string `json:"pack"`
	PackSHA256 string `json:"pack_sha256"`
	Rule       Rule   `json:"rule"`
}

type Policy struct {
	Trace *pack.PolicyTrace `json:"trace"`
	Rules []BoundRule       `json:"rules"`
}

func policyPath(name string) bool {
	if name == ".github/carl/packs.json" || name == ".github/carl/profiles.json" || name == ".github/carl/installed-packs.json" {
		return true
	}
	return strings.HasPrefix(name, ".github/instructions/") &&
		strings.HasSuffix(name, ".instructions.md") && filepath.ToSlash(filepath.Clean(name)) == name &&
		!strings.Contains(name, "\\") && !strings.Contains(name, "/../")
}

// CapturePolicy includes definitions, not only their derived effective IDs.
// Replay never consults the original policy directory or bundled defaults.
func CapturePolicy(root string) (map[string][]byte, error) {
	files := map[string][]byte{}
	total := 0
	err := filepath.WalkDir(filepath.Join(root, ".github"), func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.Type()&os.ModeSymlink != 0 {
			return fmt.Errorf("policy symlinks are not supported")
		}
		if d.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if !policyPath(rel) {
			return nil
		}
		data, err := Read(path)
		if err != nil {
			return err
		}
		total += len(data)
		if total > 2<<20 || len(files) >= 256 {
			return fmt.Errorf("policy snapshot capacity exceeded")
		}
		files[rel] = data
		return nil
	})
	if err != nil {
		return nil, err
	}
	return files, nil
}

func CompilePolicy(files map[string][]byte) (*Policy, error) {
	if len(files) > 256 || files[pack.SelectionFileName] == nil || files[pack.ProfileFileName] == nil {
		return nil, fmt.Errorf("explicit local selection and role profile required")
	}
	root, err := os.MkdirTemp("", "carl-assessment-policy-")
	if err != nil {
		return nil, err
	}
	defer os.RemoveAll(root)
	total := 0
	for name, data := range files {
		total += len(data)
		if !policyPath(name) || total > 2<<20 {
			return nil, fmt.Errorf("invalid policy snapshot path or capacity")
		}
		if strings.HasSuffix(name, ".json") && CheckJSON(data) != nil {
			return nil, fmt.Errorf("invalid policy JSON")
		}
		target := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(target), 0700); err != nil {
			return nil, err
		}
		if err := WriteNew(target, data); err != nil {
			return nil, err
		}
	}
	trace, err := pack.PolicyTraceInDir(root, nil)
	if err != nil {
		return nil, err
	}
	if trace.Context.Profile == "" || trace.Context.Role == "" {
		return nil, fmt.Errorf("explicit active profile and role required")
	}
	p := &Policy{Trace: trace, Rules: []BoundRule{}}
	for _, effective := range trace.Policies {
		if !effective.Applied {
			continue
		}
		data, exists := files[effective.CanonicalDefinition]
		if !exists {
			return nil, fmt.Errorf("effective pack must be materialized locally")
		}
		start := []byte("```carl-assessment-policy-v1\n")
		if bytes.Count(data, start) == 0 {
			continue
		}
		if bytes.Count(data, start) != 1 {
			return nil, fmt.Errorf("multiple assessment policy blocks")
		}
		_, rest, _ := bytes.Cut(data, start)
		block, _, found := bytes.Cut(rest, []byte("\n```"))
		var rules struct {
			Rules []Rule `json:"rules"`
		}
		if !found || Decode(block, &rules) != nil || len(rules.Rules) == 0 {
			return nil, fmt.Errorf("invalid assessment policy block")
		}
		var rawRules struct {
			Rules []json.RawMessage `json:"rules"`
		}
		if err := json.Unmarshal(block, &rawRules); err != nil {
			return nil, err
		}
		for _, raw := range rawRules.Rules {
			if RequireFields(raw, "id", "signal", "operator", "threshold", "action") != nil {
				return nil, fmt.Errorf("incomplete assessment rule")
			}
		}
		seen := map[string]bool{}
		sort.Slice(rules.Rules, func(i, j int) bool { return rules.Rules[i].ID < rules.Rules[j].ID })
		for _, rule := range rules.Rules {
			if !idRE.MatchString(rule.ID) || seen[rule.ID] ||
				(rule.Signal != "claim_supported" && rule.Signal != "authority_promoted" && rule.Signal != "uncertainty_adequate") ||
				(rule.Operator != "lt" && rule.Operator != "ge") ||
				math.IsNaN(rule.Threshold) || rule.Threshold < 0 || rule.Threshold > 1 ||
				(rule.Action != "challenge_required" && rule.Action != "insufficient_evidence") {
				return nil, fmt.Errorf("invalid assessment rule")
			}
			seen[rule.ID] = true
			p.Rules = append(p.Rules, BoundRule{Pack: effective.ID, PackSHA256: Hash(data), Rule: rule})
		}
	}
	if len(p.Rules) == 0 || len(p.Rules) > 256 {
		return nil, fmt.Errorf("no active assessment policy or too many rules")
	}
	return p, nil
}

type Challenge struct {
	ClaimID    string   `json:"claim_id,omitempty"`
	QuestionID string   `json:"question_id"`
	Pack       string   `json:"pack"`
	Rule       string   `json:"rule"`
	Action     string   `json:"action"`
	Quotes     []string `json:"evidence_quotes"`
}

type Decision struct {
	Disposition   string             `json:"disposition"`
	Challenges    []Challenge        `json:"challenges"`
	Signals       map[string]float64 `json:"signals"`
	ReportedModel string             `json:"reported_model"`
	Authority     string             `json:"authority"`
}

func ApplyPolicy(p *Policy, a *Assessment, native *NativeRequest, raw []byte) (*Decision, error) {
	if p == nil || a == nil || native == nil || len(p.Rules) == 0 {
		return nil, fmt.Errorf("validated_policy_and_request_required")
	}
	questions := map[string]ProviderQuestion{}
	for id, question := range native.Questions {
		if question.Type != "noul" {
			return nil, fmt.Errorf("unsupported_policy_question_type")
		}
		questions[id] = ProviderQuestion{Type: question.Type}
	}
	provider, err := ParseProvider(raw, questions)
	if err != nil {
		return nil, err
	}
	result := &Decision{Disposition: "no_challenge", Challenges: []Challenge{},
		Signals: map[string]float64{}, ReportedModel: provider.Model,
		Authority: "untrusted_challenge_not_generator_instruction"}
	for id := range native.Questions {
		result.Signals[id] = *provider.Answers[id].Noul
	}
	for _, bound := range p.Rules {
		type target struct {
			question, claim string
			quotes          []string
		}
		targets := []target{{question: bound.Rule.Signal, quotes: []string{}}}
		if bound.Rule.Signal == "claim_supported" {
			targets = nil
			for i, claim := range a.Claims {
				targets = append(targets, target{fmt.Sprintf("claim_%04d_supported", i), claim.ID, claim.Quotes})
			}
		}
		for _, target := range targets {
			value := result.Signals[target.question]
			trigger := (bound.Rule.Operator == "lt" && value < bound.Rule.Threshold) ||
				(bound.Rule.Operator == "ge" && value >= bound.Rule.Threshold)
			if !trigger {
				continue
			}
			result.Challenges = append(result.Challenges, Challenge{ClaimID: target.claim,
				QuestionID: target.question, Pack: bound.Pack, Rule: bound.Rule.ID,
				Action: bound.Rule.Action, Quotes: target.quotes})
			if result.Disposition != "insufficient_evidence" {
				result.Disposition = bound.Rule.Action
			}
		}
	}
	return result, nil
}
