package assessment

import (
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strings"
)

const ProviderResponseSchema = "mmmtap-systemone-typed-response-v1"

// ProviderQuestion does not expand the frozen Path B request question catalog.
type ProviderQuestion struct {
	Type     string            `json:"type"`
	Criteria map[string]string `json:"criteria,omitempty"`
}

type ProviderAnswer struct {
	Noul          *float64           `json:"noul,omitempty"`
	Choice        *string            `json:"choice,omitempty"`
	Probabilities map[string]float64 `json:"probabilities,omitempty"`
}

type ProviderEvidence struct {
	Model   string                    `json:"resolved_model"`
	Answers map[string]ProviderAnswer `json:"answers"`
	Usage   map[string]int64          `json:"usage"`
}

func responseObject(raw []byte, allowed ...string) (map[string]json.RawMessage, error) {
	var obj map[string]json.RawMessage
	if err := json.Unmarshal(raw, &obj); err != nil || obj == nil {
		return nil, fmt.Errorf("provider object required")
	}
	if allowed != nil {
		for name := range obj {
			found := false
			for _, field := range allowed {
				found = found || name == field
			}
			if !found {
				return nil, fmt.Errorf("unexpected provider field: %s", name)
			}
		}
	}
	return obj, nil
}

func probability(raw []byte) (float64, error) {
	var number *float64
	if err := json.Unmarshal(raw, &number); err != nil || number == nil ||
		math.IsNaN(*number) || math.IsInf(*number, 0) || *number < 0 || *number > 1 {
		return 0, fmt.Errorf("invalid provider probability")
	}
	return *number, nil
}

// ParseProvider interprets evidence only. Policy decisions belong to ApplyPolicy.
func ParseProvider(raw []byte, questions map[string]ProviderQuestion) (*ProviderEvidence, error) {
	if err := CheckJSON(raw); err != nil {
		return nil, fmt.Errorf("invalid_provider_json: %w", err)
	}
	obj, err := responseObject(raw, "model", "answers", "usage")
	if err != nil {
		return nil, err
	}
	var model string
	if err := json.Unmarshal(obj["model"], &model); err != nil || model == "" ||
		strings.TrimSpace(model) != model || strings.IndexFunc(model, func(r rune) bool { return r < 32 || r == 127 }) >= 0 {
		return nil, fmt.Errorf("invalid_provider_identity")
	}
	answers, err := responseObject(obj["answers"])
	if err != nil || len(answers) != len(questions) {
		return nil, fmt.Errorf("invalid_provider_answer_set")
	}
	evidence := &ProviderEvidence{Model: model, Answers: map[string]ProviderAnswer{}}
	for id, question := range questions {
		answer := ProviderAnswer{}
		switch question.Type {
		case "noul":
			fields, err := responseObject(answers[id], "noul")
			if err != nil {
				return nil, err
			}
			number, err := probability(fields["noul"])
			if err != nil {
				return nil, fmt.Errorf("invalid_provider_noul")
			}
			answer.Noul = &number
		case "choice":
			fields, err := responseObject(answers[id], "choice", "probabilities")
			if err != nil {
				return nil, err
			}
			var choice *string
			if err := json.Unmarshal(fields["choice"], &choice); err != nil || choice == nil {
				return nil, fmt.Errorf("invalid_provider_choice")
			}
			if _, ok := question.Criteria[*choice]; !ok {
				return nil, fmt.Errorf("invalid_provider_choice")
			}
			answer.Choice = choice
			if rawVector, exists := fields["probabilities"]; exists {
				vector, err := responseObject(rawVector)
				if err != nil || len(vector) != len(question.Criteria) {
					return nil, fmt.Errorf("invalid_provider_probabilities")
				}
				keys := make([]string, 0, len(question.Criteria))
				for key := range question.Criteria {
					keys = append(keys, key)
				}
				sort.Strings(keys)
				answer.Probabilities = map[string]float64{}
				sum := 0.0
				for _, key := range keys {
					number, err := probability(vector[key])
					if err != nil {
						return nil, err
					}
					answer.Probabilities[key] = number
					sum += number
				}
				if math.Abs(sum-1) > 0.001 {
					return nil, fmt.Errorf("invalid_provider_probability_sum")
				}
			}
		default:
			return nil, fmt.Errorf("unsupported_provider_question_type")
		}
		evidence.Answers[id] = answer
	}
	if usage, exists := obj["usage"]; exists && strings.TrimSpace(string(usage)) != "null" {
		fields, err := responseObject(usage, "input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens", "total_tokens")
		if err != nil {
			return nil, err
		}
		evidence.Usage = map[string]int64{}
		for key, rawCount := range fields {
			var count *int64
			if err := json.Unmarshal(rawCount, &count); err != nil || count == nil || *count < 0 {
				return nil, fmt.Errorf("invalid_provider_usage")
			}
			evidence.Usage[key] = *count
		}
	}
	return evidence, nil
}
