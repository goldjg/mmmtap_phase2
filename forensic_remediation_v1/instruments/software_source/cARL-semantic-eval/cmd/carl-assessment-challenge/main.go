package main

import (
	"fmt"
	"os"

	"github.com/goldjg/carl/internal/assessment"
)

func main() {
	exe, err := os.Executable()
	if err == nil {
		var data []byte
		data, err = os.ReadFile(exe)
		if err == nil {
			err = assessment.Run(os.Args[1:], os.Stdout, os.Stderr, assessment.Hash(data))
		}
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "carl-assessment-challenge: %v\n", err)
		os.Exit(1)
	}
}
