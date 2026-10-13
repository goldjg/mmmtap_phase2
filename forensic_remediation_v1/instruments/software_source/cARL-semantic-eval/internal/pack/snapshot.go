package pack

import "fmt"

// PolicyTraceInDir exposes the existing read-only discovery/profile/composition
// evaluator without printing output or changing selection.
func PolicyTraceInDir(rootDir string, arts Artifacts) (*PolicyTrace, error) {
	evaluation, err := NewExplain(arts).evaluateInDir(rootDir)
	if err != nil {
		return nil, err
	}
	if len(evaluation.Trace.Conflicts) != 0 {
		return nil, fmt.Errorf("policy composition conflicts: %s", ConflictSummary(evaluation.Trace.Conflicts))
	}
	return &evaluation.Trace, nil
}
