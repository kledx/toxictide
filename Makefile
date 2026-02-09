.PHONY: help install install-dev test test-cov lint format clean run

help:
	@echo "TOXICTIDE - 生产级量化交易系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install      - 安装生产依赖"
	@echo "  make install-dev  - 安装开发依赖"
	@echo "  make test         - 运行所有测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make lint         - 运行代码检查 (mypy + ruff)"
	@echo "  make format       - 格式化代码 (black + isort)"
	@echo "  make clean        - 清理缓存和临时文件"
	@echo "  make run          - 运行主程序 (paper trading 模式)"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest toxictide/tests/ -v

test-cov:
	pytest toxictide/tests/ --cov=toxictide --cov-report=html --cov-report=term

lint:
	@echo "Running mypy..."
	mypy toxictide/ --ignore-missing-imports || true
	@echo "Running ruff..."
	ruff check toxictide/ || true

format:
	@echo "Running black..."
	black toxictide/
	@echo "Running isort..."
	isort toxictide/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage

run:
	python toxictide/app.py --config toxictide/config/dev.yaml
