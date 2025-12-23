# Phase 1 - Testing & Quality Assurance Guide

## 🧪 Running the Test Suite

### Prerequisites
```bash
pip install pytest pytest-cov flask-testing
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_trading.py -v
pytest tests/test_api.py -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=. --cov-report=html
# Then open htmlcov/index.html in browser
```

### Run Only Fast Tests (skip slow/integration tests)
```bash
pytest tests/ -m "not slow and not integration" -v
```

---

## 🎯 Test Files Overview

### tests/test_trading.py
**Purpose**: Core trading system functionality

**Test Classes**:
- `TestTradingSystem` - Buy, sell, portfolio calculations
- `TestLeagueTrading` - League-specific trading
- `TestErrorHandling` - Edge cases and error scenarios

**Key Tests**:
- ✅ User creation and initial cash
- ✅ Buy stock with sufficient funds
- ✅ Sell stock with holdings
- ✅ Insufficient funds error
- ✅ Insufficient shares error
- ✅ Portfolio value calculation
- ✅ Transaction history chronological order
- ✅ Portfolio isolation (personal vs league)
- ✅ Error handling for edge cases

**Run**: `pytest tests/test_trading.py -v`

---

### tests/test_api.py
**Purpose**: REST API endpoint validation

**Test Classes**:
- `TestAuthEndpoints` - Login/register flows
- `TestPortfolioEndpoints` - Portfolio pages
- `TestMarketStatusAPI` - Market status endpoint
- `TestLeagueEndpoints` - League pages
- `TestErrorHandling` - HTTP error responses

**Key Tests**:
- ✅ User registration
- ✅ User login
- ✅ Invalid credentials handling
- ✅ Market status endpoint response format
- ✅ Protected endpoints require login
- ✅ 404 error handling

**Run**: `pytest tests/test_api.py -v`

---

## 🧩 Test Database

All tests use separate test databases to avoid affecting production data:
- `test_stocks.db` - Trading tests
- `test_league.db` - League tests
- `test_errors.db` - Error handling tests
- `test_db.sqlite` - Session-scoped database

These are automatically cleaned up after tests.

---

## ✅ Manual Testing Checklist

### Trading System
- [ ] Buy stock with personal portfolio
- [ ] Buy stock with league portfolio
- [ ] Sell stock with personal portfolio
- [ ] Sell stock with league portfolio
- [ ] Buy max shares button works
- [ ] Insufficient funds error shows
- [ ] Insufficient shares error shows
- [ ] Transaction appears in history
- [ ] Portfolio value updates correctly
- [ ] Copy trading executes correctly

### Portfolio & Dashboard
- [ ] Dashboard shows correct cash balance
- [ ] Dashboard shows correct holdings
- [ ] Portfolio calculations are accurate
- [ ] Holdings are isolated between personal and league
- [ ] Portfolio history chart displays
- [ ] Performance metrics are correct
- [ ] Chart updates with new trades

### Leagues
- [ ] Create league works
- [ ] Join league works
- [ ] Leave league works
- [ ] League leaderboard displays
- [ ] Leaderboard updates after trades
- [ ] Activity feed shows trades
- [ ] H2H matchups calculate correctly

### Mobile Responsiveness
- [ ] Chart displays properly on mobile
- [ ] Forms are usable on mobile
- [ ] Buttons don't overflow
- [ ] Text is readable on small screens
- [ ] Navigation works on mobile
- [ ] Modals fit on mobile screen
- [ ] No horizontal scroll

### Error Handling
- [ ] Invalid symbol shows error
- [ ] Negative values are rejected
- [ ] Zero shares are rejected
- [ ] Non-existent user handled gracefully
- [ ] Database errors show user-friendly message
- [ ] Failed API calls don't crash app

---

## 🔍 Code Quality Checks

### Type Hints
Check for type hints in critical functions:
```bash
grep -n "def " app.py | grep -v ":" | head -20
```

### Unused Imports
```bash
grep -n "^import\|^from" app.py | head -30
```

### Error Logging
Verify all try-except blocks have logging:
```bash
grep -n "except" app.py | head -20
```

---

## 📊 Test Coverage Goals

**Phase 1 Target**: 60% coverage
- Core trading: 80%
- Database operations: 75%
- API endpoints: 65%
- Error handling: 70%

**Phase 2 Target**: 80% coverage
**Phase 3 Target**: 90% coverage

---

## 🚀 CI/CD Integration

### GitHub Actions (Optional Setup)
Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install -r dev-requirements.txt
    - name: Run tests
      run: |
        pytest tests/ -v --cov=. --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 🔧 Performance Testing

### Load Testing (Optional)
For testing concurrent trades:

```bash
pip install locust
```

Create `tests/locustfile.py` for load testing scenarios.

---

## 📝 Adding New Tests

### Template for New Test File
```python
import pytest
from database.db_manager import DatabaseManager

class TestNewFeature:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = DatabaseManager("test_new.db")
        yield
        # Cleanup
    
    def test_something(self):
        """Test description"""
        result = self.db.some_method()
        assert result is not None
```

---

## 🐛 Debugging Tests

### Run with Print Statements
```bash
pytest tests/test_trading.py -v -s
```

### Run Single Test
```bash
pytest tests/test_trading.py::TestTradingSystem::test_buy_stock_success -v
```

### Run with Debugger
```bash
pytest tests/test_trading.py --pdb
```

---

## 📋 Test Status Checklist

- [x] Trading tests written
- [x] API tests written
- [x] Error handling tests written
- [ ] All tests passing
- [ ] Coverage report generated
- [ ] Manual testing completed
- [ ] Performance benchmarked
- [ ] CI/CD configured (optional)

---

## 📞 Test Troubleshooting

### Import Errors
**Issue**: `ModuleNotFoundError: No module named 'database'`
**Fix**: Run tests from project root directory

### Database Locks
**Issue**: `database is locked` error
**Fix**: Ensure test databases are using `:memory:` or separate files

### Fixture Errors
**Issue**: `fixture not found` error
**Fix**: Make sure conftest.py is in tests/ directory

---

## 🎓 Learning Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Guide](https://flask.palletsprojects.com/testing/)
- [SQLite Testing Patterns](https://www.sqlite.org/testing.html)
- [Best Practices for Test Databases](https://12factor.net/tests)

---

**Status**: Phase 1 testing framework complete ✅
**Next**: Execute full test suite and achieve 60%+ coverage
**Timeline**: 2-3 hours for comprehensive testing
