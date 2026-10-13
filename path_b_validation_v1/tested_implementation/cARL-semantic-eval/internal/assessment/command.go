package assessment

import (
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

const Usage = `Usage: carl-assessment-challenge <prepare|evaluate-offline|replay> [options]
  prepare --request FILE --policy-root DIR --out NEW_DIR
  evaluate-offline --prepared FILE --prepared-sha256 HASH --response FILE --mode mock|imported_unverified --out NEW_DIR
  replay --receipt FILE --receipt-sha256 HASH
No live execution or credentials are supported. Digests must come from a trusted external record.
`

func Run(args []string, out, errOut io.Writer, implementation string) (returnErr error) {
	if len(args) == 0 || (len(args) == 1 && (args[0] == "--help" || args[0] == "-h")) {
		_, err := io.WriteString(out, Usage)
		return err
	}
	mode := args[0]
	if mode != "prepare" && mode != "evaluate-offline" && mode != "replay" {
		return fmt.Errorf("unsupported command; live evaluation is disabled")
	}
	fs := flag.NewFlagSet(mode, flag.ContinueOnError)
	fs.SetOutput(errOut)
	var request, root, dest, prepared, prepSHA, response, evidenceMode, receipt, receiptSHA string
	switch mode {
	case "prepare":
		fs.StringVar(&request, "request", "", "frozen request file")
		fs.StringVar(&root, "policy-root", "", "explicit local cARL policy directory")
		fs.StringVar(&dest, "out", "", "new attempt directory")
	case "evaluate-offline":
		fs.StringVar(&prepared, "prepared", "", "prepared artifact")
		fs.StringVar(&prepSHA, "prepared-sha256", "", "external prepared digest")
		fs.StringVar(&response, "response", "", "mock or unverified recorded response")
		fs.StringVar(&evidenceMode, "mode", "", "mock or imported_unverified")
		fs.StringVar(&dest, "out", "", "new attempt directory")
	case "replay":
		fs.StringVar(&receipt, "receipt", "", "receipt artifact")
		fs.StringVar(&receiptSHA, "receipt-sha256", "", "external receipt digest")
	}
	if err := fs.Parse(args[1:]); err != nil {
		if err == flag.ErrHelp {
			return nil
		}
		return err
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected positional arguments")
	}
	if (mode == "prepare" && (request == "" || root == "")) ||
		(mode == "evaluate-offline" && (prepared == "" || prepSHA == "" || response == "" || evidenceMode == "")) ||
		(mode == "replay" && (receipt == "" || receiptSHA == "")) {
		return fmt.Errorf("all documented input flags are required")
	}
	if mode == "replay" {
		raw, err := Read(receipt)
		if err != nil {
			return err
		}
		replayed, err := Replay(raw, receiptSHA)
		if err != nil {
			return err
		}
		_, err = fmt.Fprintf(out, "verified offline replay: %s; live_calls=0\n", replayed.Status)
		return err
	}
	if dest == "" {
		return fmt.Errorf("new output directory required")
	}
	if err := os.Mkdir(dest, 0700); err != nil {
		return fmt.Errorf("reserve first attempt: %w", err)
	}
	defer func() {
		if returnErr == nil {
			return
		}
		failure, err := JSON(map[string]string{"schema": Version + "-failure", "status": "failed", "reason": returnErr.Error()})
		if err == nil {
			err = WriteNew(filepath.Join(dest, "failure.json"), failure)
		}
		if err != nil {
			returnErr = fmt.Errorf("%w; persist failure: %v", returnErr, err)
		}
	}()
	if err := SyncDir(filepath.Dir(dest)); err != nil {
		return err
	}
	intent, err := JSON(map[string]string{"schema": Version + "-intent", "operation": mode, "implementation_sha256": implementation})
	if err != nil {
		return err
	}
	if err := WriteNew(filepath.Join(dest, "intent.json"), intent); err != nil {
		return err
	}
	artifact, name, operationErr := execute(mode, request, root, prepared, prepSHA, response, evidenceMode, implementation, dest)
	if operationErr != nil {
		return operationErr
	}
	raw, err := JSON(artifact)
	if err != nil {
		return err
	}
	if len(raw) > MaxBytes {
		return fmt.Errorf("serialized artifact exceeds replay capacity")
	}
	if err := WriteNew(filepath.Join(dest, name), raw); err != nil {
		return err
	}
	if err := WriteNew(filepath.Join(dest, "SHA256SUMS.txt"), []byte(Hash(raw)+"  "+name+"\n")); err != nil {
		return err
	}
	if _, err := fmt.Fprintf(out, "%s  %s\n", Hash(raw), name); err != nil {
		return err
	}
	if r, ok := artifact.(*Receipt); ok && r.Status == "failed" {
		return fmt.Errorf("provider fixture rejected; failed receipt preserved")
	}
	return nil
}

func execute(mode, request, root, prepared, prepSHA, response, evidenceMode, implementation, dest string) (any, string, error) {
	if mode == "prepare" {
		raw, err := Read(request)
		if err != nil {
			return nil, "", err
		}
		if err := WriteNew(filepath.Join(dest, "request.json"), raw); err != nil {
			return nil, "", err
		}
		files, err := CapturePolicy(root)
		if err != nil {
			return nil, "", err
		}
		p, err := Prepare(raw, files, implementation)
		return p, "prepared.json", err
	}
	raw, err := Read(prepared)
	if err != nil {
		return nil, "", err
	}
	if err := WriteNew(filepath.Join(dest, "prepared.json"), raw); err != nil {
		return nil, "", err
	}
	answer, err := Read(response)
	if err != nil {
		return nil, "", err
	}
	if err := WriteNew(filepath.Join(dest, "response.json"), answer); err != nil {
		return nil, "", err
	}
	r, err := EvaluateOffline(raw, prepSHA, answer, evidenceMode, implementation)
	return r, "receipt.json", err
}
