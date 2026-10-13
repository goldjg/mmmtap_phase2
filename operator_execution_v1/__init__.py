"""Separately versioned operator execution; importing this package never infers."""
import sys

sys.dont_write_bytecode = True

VERSION = "mmmtap-operator-execution-v1"
