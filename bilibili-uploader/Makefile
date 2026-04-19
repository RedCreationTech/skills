.PHONY: install package clean

SKILL_NAME := bilibili-uploader
SKILLS_DIR := $(HOME)/.config/agents/skills

install:
	@echo "Installing skill to $(SKILLS_DIR)/$(SKILL_NAME)"
	@mkdir -p $(SKILLS_DIR)
	@rm -rf $(SKILLS_DIR)/$(SKILL_NAME)
	@cp -r . $(SKILLS_DIR)/$(SKILL_NAME)
	@echo "Done. Restart Kimi to load the skill."

package:
	@cd $(SKILLS_DIR) && zip -r $(SKILL_NAME).skill $(SKILL_NAME)
	@echo "Packaged: $(SKILLS_DIR)/$(SKILL_NAME).skill"

clean:
	@rm -f $(SKILLS_DIR)/$(SKILL_NAME).skill
