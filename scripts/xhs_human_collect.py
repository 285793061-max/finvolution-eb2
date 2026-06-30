"""
Thin shim for backward compatibility.
Delegates to scripts.xhs_collector.cli.
"""

from scripts.xhs_collector.cli import main

if __name__ == "__main__":
    main()