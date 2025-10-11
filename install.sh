#!/bin/bash

echo "Installing QRL - Quantum Resistant Ledger"
echo "---------------------------------"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is required but not installed. Please install pip3 and try again."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Install QRL in development mode
echo "Installing QRL..."
pip3 install -e .

echo ""
echo "QRL has been installed successfully!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start a QRL node, run:"
echo "  python3 -m qrl.main"
echo ""
echo "To create a wallet, run:"
echo "  python3 -m qrl.cli wallet_gen"
echo ""
echo "To start mining, run:"
echo "  python3 -m qrl.main --mine"
echo ""