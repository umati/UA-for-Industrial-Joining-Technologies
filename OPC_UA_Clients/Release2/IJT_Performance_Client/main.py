#!/usr/bin/env python3
"""
main.py — Main CLI entry point for IJT Performance Client.

Usage:
  python main.py --help
  python main.py --config profiles/single_server.yaml
  python main.py --config profiles/multi_server_fleet.yaml
  python main.py --endpoints "opc.tcp://localhost:40451" --samples 10
  python main.py -e "opc.tcp://10.0.1.11:40451,opc.tcp://10.0.1.12:40451" -d 30
"""

from __future__ import annotations

import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
