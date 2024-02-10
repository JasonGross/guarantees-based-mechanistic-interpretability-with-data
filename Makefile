PYTHON?=poetry run python
FLAKE8?=poetry run flake8
PRE_COMMIT?=poetry run pre-commit
FLAKE8_EXTRA_FLAGS?=
FLAKE8_STANDARD_FLAGS?=--count --show-source --statistics
# The GitHub editor is 127 chars wide
FLAKE8_MORE_FLAGS?=--count --max-complexity=10 --max-line-length=127 --statistics

TEST_LOAD_EXPERIMENTS = \
	exp_max_of_n \
	exp_modular_fine_tuning \
	exp_sorted_list \
	#

FORCE_LOAD ?= --force load

define add_target
# $(1) main target
# $(2) intermediate target
# $(3) recipe
$(1): $(1)-$(2)

.PHONY: $(1)-$(2)
$(1)-$(2):
	$(3)
endef

.PHONY: test-load-experiments
$(foreach e,$(TEST_LOAD_EXPERIMENTS),$(eval $(call add_target,test-load-experiments,$(e),$(PYTHON) -m gbmi.$(e).train $(FORCE_LOAD))))
$(eval $(call add_target,test-load-experiments,max-of-2-grok,$(PYTHON) -m gbmi.exp_max_of_n.train --max-of 2 --deterministic --train-for-epochs 1500 --validate-every-epochs 1 --force-adjacent-gap 0,1 --use-log1p --training-ratio 0.04638671875 $(FORCE_LOAD)))
$(eval $(call add_target,test-load-experiments,max-of-4-123,$(PYTHON) -m gbmi.exp_max_of_n.train --max-of 4 --deterministic --seed 123 --train-for-steps 3000 --lr 0.001 --betas 0.9 0.999 --optimizer AdamW --use-log1p $(FORCE_LOAD)))

# Python syntax errors or undefined names
.PHONY: git-lint
git-lint:
	git ls-files "*.py" | xargs $(FLAKE8) --select=E9,F63,F7,F82 $(FLAKE8_STANDARD_FLAGS) $(FLAKE8_EXTRA_FLAGS)

.PHONY: git-lint-more
git-lint-more:
	git ls-files "*.py" | xargs $(FLAKE8) $(FLAKE8_MORE_FLAGS) $(FLAKE8_EXTRA_FLAGS)

.PHONY: sort-mailmap
sort-mailmap:
	{ grep '^#' .mailmap; grep '^\s*$$' .mailmap; grep '^[^#]' .mailmap | sort -f; } > .mailmap.tmp
	mv .mailmap.tmp .mailmap

.PHONY: pre-commit-install
pre-commit-install:
	$(PRE_COMMIT) install

.PHONY: pre-commit
pre-commit:
	$(PRE_COMMIT) run --all-files
