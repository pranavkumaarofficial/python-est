#!/usr/bin/env python3
"""
Python-EST: Enterprise EST Protocol Server
Main entry point for the Python-EST server.
"""
import sys
import os
import argparse
import configparser
from python_est.core.secureserver import SecureServer

def main():
    parser = argparse.ArgumentParser(description='Python-EST Server')
    parser.add_argument('-c', '--config', default='python_est.cfg', 
                       help='Configuration file path')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug mode')
    args = parser.parse_args()
    
    # Check configuration file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)
    
    # Load config to get port for display
    config = configparser.ConfigParser()
    config.read(args.config)
    port = config.get('Daemon', 'port', fallback='8443')
    address = config.get('Daemon', 'address', fallback='0.0.0.0')
    
    # Import EST handler
    from python_est.core.est_handler import ESTSrvHandler
    
    # Start EST server  
    try:
        server = SecureServer((address, int(port)), ESTSrvHandler, cfg_file=args.config)
        print(f"Starting Python-EST server on {address}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Python-EST server...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()