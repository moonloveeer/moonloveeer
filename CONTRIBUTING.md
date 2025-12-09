# Contributing to QRL

Thank you for your interest in contributing to QRL! This guide will help you get started.

## Getting Started

### Prerequisites
- Python 3.12+
- Git
- Basic understanding of blockchain concepts

### Setup
1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/moonloveeer.git
   cd moonloveeer
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow the existing code style
- Add tests for new features
- Update documentation

### 3. Test Your Changes
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_specific.py

# Test with coverage
pytest --cov=qrl tests/
```

### 4. Submit a Pull Request
- Push to your fork
- Create a pull request
- Wait for review

## Code Style

### Python
- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black default)

### JavaScript
- Use 2 spaces for indentation
- Use semicolons
- Prefer const/let over var

## Testing

### Test Structure
- Unit tests in `tests/`
- Integration tests for API endpoints
- Property-based tests with Hypothesis

### Running Tests
```bash
# Quick test
pytest tests/ -v

# With coverage
pytest --cov=qrl --cov-report=html tests/

# Specific test file
pytest tests/test_wallet_send.py -v
```

## Documentation

### API Documentation
- Update `docs/api.md` for API changes
- Include examples
- Document error responses

### Code Comments
- Comment complex logic
- Document public functions
- Use type hints

## Security

### Reporting Security Issues
- Do not open a public issue
- Email: security@qrl.dev
- Include details and reproduction steps

### Security Best Practices
- Never commit secrets
- Use environment variables
- Validate all inputs
- Follow OWASP guidelines

## Areas of Contribution

### High Priority
1. Payment integration (Coinbase Commerce)
2. Test coverage improvements
3. Security hardening
4. Documentation

### Medium Priority
1. UI/UX improvements
2. Performance optimization
3. Mobile wallet app
4. Advanced features

### Low Priority
1. Nice-to-have features
2. Code cleanup
3. Minor bug fixes

## Review Process

1. Automated checks must pass
2. At least one human review required
3. Maintainer approval for merge
4. Squash commits before merge

## Community

### Communication
- GitHub Issues: Bug reports, feature requests
- GitHub Discussions: General questions
- Discord: Real-time chat

### Code of Conduct
- Be respectful
- Be helpful
- Be inclusive
- No harassment or discrimination

## Release Process

1. Update version in `qrl/__init__.py`
2. Update CHANGELOG.md
3. Create release tag
4. Deploy to production

## Getting Help

### Resources
- [README.md](README.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)

### Questions
- Open an issue
- Start a discussion
- Join Discord

Thank you for contributing to QRL!
