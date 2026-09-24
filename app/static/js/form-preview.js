(() => {
  const root = document.querySelector("[data-form-preview]");
  if (!root) {
    return;
  }

  const form = root.querySelector("form");
  if (!form) {
    return;
  }

  const kind = root.dataset.formPreview;
  let objectUrl = "";
  let lastFile = null;

  function fieldValue(name) {
    const field = form.elements[name];
    return field ? String(field.value || "").trim() : "";
  }

  function selectedOption(name) {
    const field = form.elements[name];
    if (!field || field.selectedIndex < 0) {
      return null;
    }
    return field.options[field.selectedIndex];
  }

  function optionData(name, key) {
    const option = selectedOption(name);
    if (!option || !option.value) {
      return "";
    }
    return option.dataset[key] || "";
  }

  function text(selector, value) {
    const node = root.querySelector(selector);
    if (node) {
      node.textContent = value;
    }
  }

  function setHidden(selector, hidden) {
    const node = root.querySelector(selector);
    if (node) {
      node.hidden = hidden;
    }
  }

  function selectedFileUrl() {
    const input = form.querySelector('input[type="file"][name="image"]');
    const file = input && input.files && input.files[0] ? input.files[0] : null;
    if (file && file === lastFile) {
      return objectUrl;
    }
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = "";
    }
    lastFile = file;
    if (!file) {
      return "";
    }
    objectUrl = URL.createObjectURL(file);
    return objectUrl;
  }

  function setThumb(selector, url) {
    const visual = root.querySelector(selector);
    if (!visual) {
      return;
    }
    const image = visual.querySelector("img");
    const placeholder = visual.querySelector("[data-selected-placeholder]");
    if (url) {
      if (image) {
        image.src = url;
        image.hidden = false;
      }
      if (placeholder) {
        placeholder.hidden = true;
      }
    } else {
      if (image) {
        image.removeAttribute("src");
        image.hidden = true;
      }
      if (placeholder) {
        placeholder.hidden = false;
      }
    }
  }

  function updateSelectedFabrics() {
    const section = root.querySelector("[data-selected-fabrics]");
    if (!section) {
      return;
    }
    const outerName = optionData("outer_fabric_id", "name");
    const liningName = optionData("lining_fabric_id", "name");
    const outerYards = optionData("outer_fabric_id", "yards");
    const liningYards = optionData("lining_fabric_id", "yards");
    section.hidden = !outerName && !liningName;
    setHidden("[data-selected-outer]", !outerName);
    setHidden("[data-selected-lining]", !liningName);
    if (outerName) {
      text("[data-selected-outer-name]", outerName);
      text("[data-selected-outer-yards]", outerYards === "" ? "" : `${outerYards} yd on hand`);
      setThumb("[data-selected-outer-visual]", optionData("outer_fabric_id", "image"));
    }
    if (liningName) {
      text("[data-selected-lining-name]", liningName);
      text("[data-selected-lining-yards]", liningYards === "" ? "" : `${liningYards} yd on hand`);
      setThumb("[data-selected-lining-visual]", optionData("lining_fabric_id", "image"));
    }
  }

  function setVisual(url) {
    const visual = root.querySelector("[data-preview-visual]");
    if (!visual) {
      return;
    }
    const image = visual.querySelector("img");
    const placeholder = visual.querySelector("[data-preview-placeholder]");
    if (url) {
      if (image) {
        image.src = url;
        image.hidden = false;
      }
      if (placeholder) {
        placeholder.hidden = true;
      }
    } else {
      if (image) {
        image.removeAttribute("src");
        image.hidden = true;
      }
      if (placeholder) {
        placeholder.hidden = false;
      }
    }
  }

  function statusClass(status) {
    return `status-label status-label--${status.toLowerCase().replace(/ /g, "-")}`;
  }

  function enoughLabel(available, required) {
    const have = Number(available);
    const need = Number(required);
    if (!Number.isFinite(have) || !Number.isFinite(need)) {
      return null;
    }
    return have >= need ? "Yes" : "No";
  }

  function setEnough(selector, label) {
    const node = root.querySelector(selector);
    const result = node && node.querySelector("[data-yardage-result]");
    if (!result) {
      return;
    }
    result.textContent = label || "";
    result.classList.toggle("yardage-result--yes", label === "Yes");
    result.classList.toggle("yardage-result--no", label === "No");
  }

  function updateProject() {
    const name = fieldValue("name") || "Untitled project";
    const status = fieldValue("status") || "In Progress";
    const patternName = optionData("pattern_id", "name") || "Choose a pattern";
    const outerName = optionData("outer_fabric_id", "name") || "Choose outer fabric";
    const liningName = optionData("lining_fabric_id", "name");
    const image =
      selectedFileUrl() ||
      root.dataset.currentImage ||
      optionData("pattern_id", "image") ||
      optionData("outer_fabric_id", "image");

    text("[data-preview-name]", name);
    text("[data-preview-pattern]", patternName);
    text("[data-preview-fabric]", outerName);
    text("[data-preview-lining]", liningName ? `Lining: ${liningName}` : "");
    setHidden("[data-preview-lining]", !liningName);

    const statusNode = root.querySelector("[data-preview-status]");
    if (statusNode) {
      statusNode.textContent = status;
      statusNode.className = statusClass(status);
    }
    setVisual(image);
    updateSelectedFabrics();

    const patternSelected = Boolean(optionData("pattern_id", "name"));
    const yardage = root.querySelector("[data-preview-yardage]");
    if (!yardage) {
      return;
    }
    yardage.hidden = !patternSelected;
    if (!patternSelected) {
      return;
    }

    const hours = optionData("pattern_id", "hours");
    const outerRequired = optionData("pattern_id", "outerYards");
    const liningRequired = optionData("pattern_id", "liningYards");
    const outerAvailable = optionData("outer_fabric_id", "yards");
    const liningAvailable = optionData("lining_fabric_id", "yards");
    const requiresLining = liningRequired !== "";

    text("[data-yardage-hours]", `Estimated time: ${hours} hours`);
    text("[data-yardage-outer-required]", `Pattern requires: ${outerRequired} yards`);

    const outerDetails = root.querySelector("[data-yardage-outer-details]");
    const outerMissing = root.querySelector("[data-yardage-outer-missing]");
    if (outerAvailable) {
      if (outerDetails) {
        outerDetails.hidden = false;
      }
      if (outerMissing) {
        outerMissing.hidden = true;
      }
      text("[data-yardage-outer-available]", `Selected fabric available: ${outerAvailable} yards`);
      setEnough("[data-yardage-outer-enough]", enoughLabel(outerAvailable, outerRequired));
    } else {
      if (outerDetails) {
        outerDetails.hidden = true;
      }
      if (outerMissing) {
        outerMissing.hidden = false;
      }
    }

    const liningBlock = root.querySelector("[data-yardage-lining]");
    const noLining = root.querySelector("[data-yardage-no-lining]");
    if (requiresLining) {
      if (liningBlock) {
        liningBlock.hidden = false;
      }
      if (noLining) {
        noLining.hidden = true;
        noLining.textContent = "";
      }
      text("[data-yardage-lining-required]", `Pattern requires: ${liningRequired} yards`);
      const liningDetails = root.querySelector("[data-yardage-lining-details]");
      const liningNeeded = root.querySelector("[data-yardage-lining-needed]");
      if (liningAvailable) {
        if (liningDetails) {
          liningDetails.hidden = false;
        }
        if (liningNeeded) {
          liningNeeded.hidden = true;
        }
        text(
          "[data-yardage-lining-available]",
          `Selected fabric available: ${liningAvailable} yards`
        );
        setEnough(
          "[data-yardage-lining-enough]",
          enoughLabel(liningAvailable, liningRequired)
        );
      } else {
        if (liningDetails) {
          liningDetails.hidden = true;
        }
        if (liningNeeded) {
          liningNeeded.hidden = false;
          liningNeeded.textContent = "Lining is still needed.";
        }
      }
    } else {
      if (liningBlock) {
        liningBlock.hidden = true;
      }
      if (noLining) {
        noLining.hidden = false;
        noLining.textContent = "This pattern does not require lining.";
      }
    }
  }

  function updatePattern() {
    const name = fieldValue("name") || "Untitled pattern";
    const hours = fieldValue("estimated_hours");
    const outer = fieldValue("outer_yards_required");
    const lining = fieldValue("lining_yards_required");
    text("[data-preview-name]", name);
    text("[data-preview-meta]", [
      hours ? `${hours} hr` : null,
      outer ? `${outer} yd outer` : null,
    ].filter(Boolean).join(" · ") || "Add time and yardage");
    text(
      "[data-preview-lining]",
      lining === "" ? "Does not require lining" : `Lining fabric: ${lining} yards`
    );
    setVisual(selectedFileUrl() || root.dataset.currentImage || "");
  }

  function updateFabric() {
    const name = fieldValue("name") || "New fabric";
    const yards = fieldValue("yards_available");
    const description = fieldValue("description");
    text("[data-preview-name]", name);
    text("[data-preview-yards]", yards === "" ? "Add yardage" : `${yards} yd available`);
    text("[data-preview-description]", description);
    setHidden("[data-preview-description]", !description);
    setVisual(selectedFileUrl() || root.dataset.currentImage || "");
  }

  function update() {
    if (kind === "project") {
      updateProject();
    } else if (kind === "pattern") {
      updatePattern();
    } else if (kind === "fabric") {
      updateFabric();
    }
  }

  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
})();
