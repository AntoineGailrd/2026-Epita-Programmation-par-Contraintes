const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");

const candidateForm = document.getElementById("candidate-form");
const jobForm = document.getElementById("job-form");
const candidateList = document.getElementById("candidate-list");
const jobList = document.getElementById("job-list");
const candidateStatus = document.getElementById("candidate-status");
const jobStatus = document.getElementById("job-status");
const compatibilityStatus = document.getElementById("compatibility-status");
const compatibilityMeta = document.getElementById("compatibility-meta");
const compatibilityResults = document.getElementById("compatibility-results");
const compatibilityCandidateFilter = document.getElementById("compatibility-candidate-filter");
const compatibilityJobFilter = document.getElementById("compatibility-job-filter");
const compatibilityTopK = document.getElementById("compatibility-top-k");
const runCompatibilityButton = document.getElementById("run-compatibility");
const validationTargets = document.querySelectorAll("input, textarea, select");

let cachedCandidates = [];
let cachedJobs = [];

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.tab;

    tabButtons.forEach((item) => item.classList.toggle("active", item === button));
    tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `${target}-panel`));
  });
});

function splitList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseSkillBlock(value, category) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [name, rawLevel] = item.split(":").map((part) => part.trim());
      const numericLevel = Number.parseInt(rawLevel || "3", 10);
      return {
        name,
        level: Number.isNaN(numericLevel) ? 3 : Math.min(Math.max(numericLevel, 1), 5),
        category,
      };
    });
}

function selectedValuesByName(form, name) {
  return Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map((input) => input.value);
}

function setStatus(target, message, isError = false) {
  target.textContent = message;
  target.style.color = isError ? "#b91c1c" : "#0f766e";
}

function normalizeOptionalNumber(value) {
  if (!value) {
    return null;
  }
  return Number.parseInt(value, 10);
}

function frenchValidationMessage(field) {
  const { validity } = field;

  if (validity.valueMissing) {
    return "Ce champ est obligatoire.";
  }
  if (validity.typeMismatch && field.type === "email") {
    return "Veuillez saisir une adresse email valide.";
  }
  if (validity.badInput || validity.typeMismatch) {
    return "La valeur saisie n'est pas valide.";
  }
  if (validity.rangeUnderflow) {
    return `La valeur minimale autorisée est ${field.min}.`;
  }
  if (validity.rangeOverflow) {
    return `La valeur maximale autorisée est ${field.max}.`;
  }
  if (validity.tooShort) {
    return `Veuillez saisir au moins ${field.minLength} caractères.`;
  }
  if (validity.tooLong) {
    return `Veuillez saisir au maximum ${field.maxLength} caractères.`;
  }
  return "";
}

function attachFrenchValidation() {
  validationTargets.forEach((field) => {
    field.addEventListener("invalid", () => {
      field.setCustomValidity(frenchValidationMessage(field));
    });

    field.addEventListener("input", () => {
      field.setCustomValidity("");
    });

    field.addEventListener("change", () => {
      field.setCustomValidity("");
    });
  });
}

function candidatePayload(form) {
  return {
    full_name: form.full_name.value.trim(),
    email: form.email.value.trim() || null,
    current_title: form.current_title.value.trim() || null,
    years_experience: Number.parseInt(form.years_experience.value || "0", 10),
    location: {
      city: form.location_city.value.trim(),
      country: form.location_country.value.trim() || "France",
      remote_preference: form.location_remote_preference.value,
      mobility_km: Number.parseInt(form.location_mobility_km.value || "0", 10),
    },
    skills: [
      ...parseSkillBlock(form.skills_technical.value, "technical"),
      ...parseSkillBlock(form.skills_functional.value, "functional"),
      ...parseSkillBlock(form.skills_language.value, "language"),
    ],
    education: {
      degree: form.education_degree.value.trim() || null,
      field_of_study: form.education_field_of_study.value.trim() || null,
      certifications: splitList(form.education_certifications.value),
    },
    preferences: {
      target_roles: splitList(form.preferences_target_roles.value),
      target_sectors: splitList(form.preferences_target_sectors.value),
      contract_types: selectedValuesByName(form, "preferences_contract_types"),
      salary_min: normalizeOptionalNumber(form.preferences_salary_min.value),
      values: splitList(form.preferences_values.value),
    },
    motivation: {
      free_text: form.motivation_free_text.value.trim(),
      drivers: splitList(form.motivation_drivers.value),
      mission_preferences: splitList(form.motivation_mission_preferences.value),
    },
    potential: {
      learning_goals: splitList(form.potential_learning_goals.value),
      transferable_experiences: form.potential_transferable_experiences.value.trim(),
      growth_domains: splitList(form.potential_growth_domains.value),
    },
    availability: {
      start_date: form.availability_start_date.value || null,
      schedule: form.availability_schedule.value,
      constraints: form.availability_constraints.value.trim(),
    },
  };
}

function jobPayload(form) {
  return {
    title: form.title.value.trim(),
    team: form.team.value.trim() || null,
    location: {
      city: form.location_city.value.trim(),
      country: form.location_country.value.trim() || "France",
      work_mode: form.location_work_mode.value,
    },
    requirements: {
      minimum_degree: form.requirements_minimum_degree.value.trim() || null,
      minimum_years_experience: Number.parseInt(
        form.requirements_minimum_years_experience.value || "0",
        10,
      ),
      mandatory_skills: splitList(form.requirements_mandatory_skills.value),
      languages: splitList(form.requirements_languages.value),
    },
    desired_skills: parseSkillBlock(form.desired_skills.value, "technical"),
    missions: form.missions.value.trim(),
    environment: {
      team_style: form.environment_team_style.value.trim(),
      pace: form.environment_pace.value.trim(),
      culture_keywords: splitList(form.environment_culture_keywords.value),
    },
    conditions: {
      salary_min: normalizeOptionalNumber(form.conditions_salary_min.value),
      salary_max: normalizeOptionalNumber(form.conditions_salary_max.value),
      contract_type: form.conditions_contract_type.value,
      start_date: form.conditions_start_date.value || null,
      capacity: Number.parseInt(form.conditions_capacity.value || "1", 10),
    },
    target_profile: {
      expected_traits: splitList(form.target_profile_expected_traits.value),
      growth_potential: form.target_profile_growth_potential.value.trim(),
      learning_expectations: splitList(form.target_profile_learning_expectations.value),
    },
  };
}

async function saveRecord(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Request failed");
  }

  return response.json();
}

function fillSelectOptions(select, items, getLabel) {
  const placeholder = select.querySelector('option[value=""]');
  select.innerHTML = "";
  if (placeholder) {
    select.appendChild(placeholder);
  }

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = getLabel(item);
    select.appendChild(option);
  });
}

function formatList(values, fallback = "Non renseigné") {
  return values && values.length ? values.join(", ") : fallback;
}

function formatSkills(skills, fallback = "Non renseigné") {
  return skills && skills.length
    ? skills.map((skill) => `${skill.name} (${skill.level}/5)`).join(", ")
    : fallback;
}

function renderTags(values, fallback = "Non renseigné") {
  if (!values || !values.length) {
    return `<span class="inline-text">${fallback}</span>`;
  }

  return `
    <div class="tag-list">
      ${values.map((value) => `<span class="info-tag">${value}</span>`).join("")}
    </div>
  `;
}

function renderDetailRows(rows) {
  return `
    <div class="detail-rows">
      ${rows
        .map(
          (row) => `
            <div class="detail-row">
              <span class="detail-label">${row.label}</span>
              <span class="detail-value">${row.value || "Non renseigné"}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderCandidateList(items) {
  if (!items.length) {
    candidateList.innerHTML = "<p class=\"record-meta\">Aucun candidat enregistré.</p>";
    return;
  }

  candidateList.innerHTML = items
    .map(
      (item) => `
        <article class="record-item expandable-item" data-expanded="false">
          <button type="button" class="expandable-toggle" aria-expanded="false">
            <span class="expandable-main">
              <h3>${item.full_name}</h3>
              <p class="record-meta">${item.current_title || "Titre non renseigné"} • ${item.location.city} • ${item.years_experience} an(s)</p>
              <p class="record-meta">Compétences: ${item.skills.length} • Moteurs: ${formatList(item.motivation.drivers, "non renseignés")}</p>
            </span>
            <span class="toggle-label">
              <span class="toggle-text">Voir le profil</span>
              <span class="toggle-arrow" aria-hidden="true">▾</span>
            </span>
          </button>
          <div class="expandable-details" hidden>
            <div class="detail-grid">
              <div class="detail-card">
                <strong>Localisation</strong>
                ${renderDetailRows([
                  { label: "Ville", value: `${item.location.city}, ${item.location.country}` },
                  { label: "Mode", value: item.location.remote_preference },
                  { label: "Mobilité", value: `${item.location.mobility_km} km` },
                ])}
              </div>
              <div class="detail-card">
                <strong>Formation</strong>
                ${renderDetailRows([
                  { label: "Diplôme", value: item.education.degree || "Non renseigné" },
                  { label: "Domaine", value: item.education.field_of_study || "Non renseigné" },
                ])}
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Compétences</strong>
                ${renderTags(item.skills.map((skill) => `${skill.name} ${skill.level}/5`), "Non renseigné")}
              </div>
              <div class="detail-card">
                <strong>Préférences</strong>
                ${renderDetailRows([
                  { label: "Salaire min", value: item.preferences.salary_min ? `${item.preferences.salary_min} EUR` : "Non renseigné" },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Postes visés</span>
                  ${renderTags(item.preferences.target_roles)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Secteurs</span>
                  ${renderTags(item.preferences.target_sectors)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Contrats</span>
                  ${renderTags(item.preferences.contract_types)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Motivation</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Texte libre</span>
                  <p class="detail-paragraph">${item.motivation.free_text}</p>
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Moteurs</span>
                  ${renderTags(item.motivation.drivers)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Potentiel</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Objectifs d'apprentissage</span>
                  ${renderTags(item.potential.learning_goals)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Domaines de progression</span>
                  ${renderTags(item.potential.growth_domains)}
                </div>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Expériences transférables</strong>
                <p class="detail-paragraph">${item.potential.transferable_experiences || "Non renseigné"}</p>
              </div>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderJobList(items) {
  if (!items.length) {
    jobList.innerHTML = "<p class=\"record-meta\">Aucun poste enregistré.</p>";
    return;
  }

  jobList.innerHTML = items
    .map(
      (item) => `
        <article class="record-item expandable-item" data-expanded="false">
          <button type="button" class="expandable-toggle" aria-expanded="false">
            <span class="expandable-main">
              <h3>${item.title}</h3>
              <p class="record-meta">${item.team || "Équipe non renseignée"} • ${item.location.city} • ${item.location.work_mode}</p>
              <p class="record-meta">Capacité: ${item.conditions.capacity} • Exigences: ${formatList(item.requirements.mandatory_skills, "aucune")}</p>
            </span>
            <span class="toggle-label">
              <span class="toggle-text">Voir le poste</span>
              <span class="toggle-arrow" aria-hidden="true">▾</span>
            </span>
          </button>
          <div class="expandable-details" hidden>
            <div class="detail-grid">
              <div class="detail-card">
                <strong>Localisation</strong>
                ${renderDetailRows([
                  { label: "Ville", value: `${item.location.city}, ${item.location.country}` },
                  { label: "Mode", value: item.location.work_mode },
                ])}
              </div>
              <div class="detail-card">
                <strong>Conditions</strong>
                ${renderDetailRows([
                  { label: "Contrat", value: item.conditions.contract_type.toUpperCase() },
                  { label: "Capacité", value: `${item.conditions.capacity} place(s)` },
                  {
                    label: "Salaire",
                    value: `${item.conditions.salary_min || "?"} - ${item.conditions.salary_max || "?"} EUR`,
                  },
                ])}
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Missions</strong>
                <p class="detail-paragraph">${item.missions}</p>
              </div>
              <div class="detail-card">
                <strong>Exigences dures</strong>
                ${renderDetailRows([
                  { label: "Diplôme", value: item.requirements.minimum_degree || "Non renseigné" },
                  { label: "Expérience", value: `${item.requirements.minimum_years_experience} an(s)` },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Compétences obligatoires</span>
                  ${renderTags(item.requirements.mandatory_skills)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Compétences souhaitées</strong>
                ${renderTags(item.desired_skills.map((skill) => `${skill.name} ${skill.level}/5`), "Non renseigné")}
              </div>
              <div class="detail-card">
                <strong>Environnement</strong>
                ${renderDetailRows([
                  { label: "Style d'équipe", value: item.environment.team_style || "Non renseigné" },
                  { label: "Rythme", value: item.environment.pace || "Non renseigné" },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Culture</span>
                  ${renderTags(item.environment.culture_keywords)}
                </div>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Profil recherché</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Traits attendus</span>
                  ${renderTags(item.target_profile.expected_traits)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Apprentissage attendu</span>
                  ${renderTags(item.target_profile.learning_expectations)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Potentiel d'évolution</span>
                  <p class="detail-paragraph">${item.target_profile.growth_potential || "Non renseigné"}</p>
                </div>
              </div>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

async function loadCandidates() {
  const response = await fetch("/api/candidates");
  const items = await response.json();
  cachedCandidates = items;
  renderCandidateList(items);
  fillSelectOptions(
    compatibilityCandidateFilter,
    items,
    (item) => `${item.full_name} - ${item.current_title || "Profil sans titre"}`,
  );
}

async function loadJobs() {
  const response = await fetch("/api/jobs");
  const items = await response.json();
  cachedJobs = items;
  renderJobList(items);
  fillSelectOptions(
    compatibilityJobFilter,
    items,
    (item) => `${item.title} - ${item.location.city}`,
  );
}

function renderCompatibilityResults(payload) {
  const results = payload.results || [];
  compatibilityMeta.textContent = `Mode embeddings: ${payload.embedding_mode} • Modèle: ${payload.embedding_model} • Résultats: ${results.length}`;

  if (!results.length) {
    compatibilityResults.innerHTML = "<p class=\"record-meta\">Aucun résultat à afficher.</p>";
    return;
  }

  const groupedByJob = results.reduce((groups, item) => {
    if (!groups[item.job_id]) {
      groups[item.job_id] = {
        jobTitle: item.job_title,
        items: [],
      };
    }
    groups[item.job_id].items.push(item);
    return groups;
  }, {});

  compatibilityResults.innerHTML = Object.values(groupedByJob)
    .sort((left, right) => left.jobTitle.localeCompare(right.jobTitle, "fr"))
    .map((group) => {
      const sortedItems = [...group.items].sort((left, right) => right.overall_score - left.overall_score);
      const averageScore = Math.round(
        sortedItems.reduce((sum, item) => sum + item.overall_score, 0) / sortedItems.length,
      );

      const cardsHtml = sortedItems
        .map((item) => {
      const criteriaHtml = item.criteria
        .map(
          (criterion) => `
            <div class="criterion-pill">
              <strong>${criterion.score}%</strong>
              <span>${criterion.label}</span>
              <span>Source: ${criterion.source}</span>
            </div>
          `,
        )
        .join("");

      const penaltiesHtml = (item.penalties || [])
        .map((penalty) => `<span class="badge">${penalty.label}</span>`)
        .join("");

      const explanationsHtml = item.criteria
        .map(
          (criterion) => `
            <div class="explanation-item">
              <div class="explanation-head">
                <strong>${criterion.label}</strong>
                <span>${criterion.score}% • poids ${criterion.weight} • source ${criterion.source}</span>
              </div>
              <p>${criterion.explanation}</p>
            </div>
          `,
        )
        .join("");

      const penaltyDetailsHtml = (item.penalties || []).length
        ? `
          <div class="explanation-group">
            <h4>Pénalités appliquées</h4>
            ${(item.penalties || [])
              .map(
                (penalty) => `
                  <div class="explanation-item">
                    <div class="explanation-head">
                      <strong>${penalty.label}</strong>
                      <span>facteur ${penalty.factor}</span>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        `
        : "";

      return `
        <article class="record-item compatibility-item" data-expanded="false">
          <button type="button" class="compatibility-toggle" aria-expanded="false">
            <span class="compatibility-header-main">
              <span class="compatibility-kicker">Compatibilité candidat-poste</span>
              <h3>${item.candidate_name} -> ${item.job_title}</h3>
              <p class="record-meta">Score brut ${Math.round(item.base_score)}% avant pénalités éventuelles</p>
            </span>
            <span class="compatibility-header-side">
              <span class="overall-score-card">
                <span class="overall-score-value">${item.overall_score}%</span>
                <span class="overall-score-label">Compatibilité globale</span>
              </span>
              <span class="toggle-label">
                <span class="toggle-text">Voir les explications</span>
                <span class="toggle-arrow" aria-hidden="true">▾</span>
              </span>
            </span>
          </button>
          <div class="criteria-grid">${criteriaHtml}</div>
          <p class="summary">${item.summary}</p>
          ${penaltiesHtml ? `<div class="badge-row">${penaltiesHtml}</div>` : ""}
          <div class="compatibility-details" hidden>
            <div class="explanation-group">
              <h4>Explications par critère</h4>
              ${explanationsHtml}
            </div>
            ${penaltyDetailsHtml}
          </div>
        </article>
      `;
        })
        .join("");

      return `
        <section class="compatibility-group" data-expanded="false">
          <button type="button" class="compatibility-group-toggle" aria-expanded="false">
            <div class="compatibility-group-header">
              <div>
                <p class="compatibility-group-kicker">Poste</p>
                <h3>${group.jobTitle}</h3>
              </div>
              <div class="compatibility-group-metrics">
                <span class="badge">${sortedItems.length} candidat(s)</span>
                <span class="badge">Moyenne ${averageScore}%</span>
                <span class="group-toggle-label">
                  <span class="group-toggle-text">Voir les compatibilités</span>
                  <span class="toggle-arrow" aria-hidden="true">▾</span>
                </span>
              </div>
            </div>
          </button>
          <div class="compatibility-group-list" hidden>
            ${cardsHtml}
          </div>
        </section>
      `;
    })
    .join("");
}

candidateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus(candidateStatus, "Enregistrement en cours...");

  try {
    await saveRecord("/api/candidates", candidatePayload(candidateForm));
    candidateForm.reset();
    candidateForm.location_country.value = "France";
    candidateForm.location_remote_preference.value = "hybrid";
    candidateForm.availability_schedule.value = "full_time";
    setStatus(candidateStatus, "Candidat enregistré.");
    await loadCandidates();
  } catch (error) {
    setStatus(candidateStatus, `Erreur: ${error.message}`, true);
  }
});

jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus(jobStatus, "Enregistrement en cours...");

  try {
    await saveRecord("/api/jobs", jobPayload(jobForm));
    jobForm.reset();
    jobForm.location_country.value = "France";
    jobForm.location_work_mode.value = "hybrid";
    jobForm.conditions_contract_type.value = "cdi";
    jobForm.conditions_capacity.value = "1";
    setStatus(jobStatus, "Poste enregistré.");
    await loadJobs();
  } catch (error) {
    setStatus(jobStatus, `Erreur: ${error.message}`, true);
  }
});

document.getElementById("refresh-candidates").addEventListener("click", () => {
  loadCandidates().catch((error) => setStatus(candidateStatus, `Erreur: ${error.message}`, true));
});

document.getElementById("refresh-jobs").addEventListener("click", () => {
  loadJobs().catch((error) => setStatus(jobStatus, `Erreur: ${error.message}`, true));
});

runCompatibilityButton.addEventListener("click", async () => {
  setStatus(compatibilityStatus, "Calcul en cours...");

  try {
    const payload = {
      candidate_ids: compatibilityCandidateFilter.value ? [compatibilityCandidateFilter.value] : [],
      job_ids: compatibilityJobFilter.value ? [compatibilityJobFilter.value] : [],
      top_k_per_candidate: Number.parseInt(compatibilityTopK.value || "5", 10),
    };

    const response = await saveRecord("/api/compatibility", payload);
    renderCompatibilityResults(response);
    setStatus(compatibilityStatus, "Calcul terminé.");
  } catch (error) {
    compatibilityMeta.textContent = "";
    compatibilityResults.innerHTML = "";
    setStatus(compatibilityStatus, `Erreur: ${error.message}`, true);
  }
});

compatibilityResults.addEventListener("click", (event) => {
  const groupToggle = event.target.closest(".compatibility-group-toggle");
  if (groupToggle) {
    const group = groupToggle.closest(".compatibility-group");
    const details = group.querySelector(".compatibility-group-list");
    const isExpanded = groupToggle.getAttribute("aria-expanded") === "true";

    groupToggle.setAttribute("aria-expanded", String(!isExpanded));
    group.dataset.expanded = String(!isExpanded);
    details.hidden = isExpanded;

    const text = groupToggle.querySelector(".group-toggle-text");
    text.textContent = isExpanded ? "Voir les compatibilités" : "Masquer les compatibilités";
    return;
  }

  const toggle = event.target.closest(".compatibility-toggle");
  if (!toggle) {
    return;
  }

  const article = toggle.closest(".compatibility-item");
  const details = article.querySelector(".compatibility-details");
  const isExpanded = toggle.getAttribute("aria-expanded") === "true";

  toggle.setAttribute("aria-expanded", String(!isExpanded));
  article.dataset.expanded = String(!isExpanded);
  details.hidden = isExpanded;

  const text = toggle.querySelector(".toggle-text");
  text.textContent = isExpanded ? "Voir les explications" : "Masquer les explications";
});

function handleExpandableListClick(event, openText, closeText) {
  const toggle = event.target.closest(".expandable-toggle");
  if (!toggle) {
    return;
  }

  const article = toggle.closest(".expandable-item");
  const details = article.querySelector(".expandable-details");
  const isExpanded = toggle.getAttribute("aria-expanded") === "true";

  toggle.setAttribute("aria-expanded", String(!isExpanded));
  article.dataset.expanded = String(!isExpanded);
  details.hidden = isExpanded;

  const text = toggle.querySelector(".toggle-text");
  text.textContent = isExpanded ? openText : closeText;
}

candidateList.addEventListener("click", (event) => {
  handleExpandableListClick(event, "Voir le profil", "Masquer le profil");
});

jobList.addEventListener("click", (event) => {
  handleExpandableListClick(event, "Voir le poste", "Masquer le poste");
});

loadCandidates().catch(() => renderCandidateList([]));
loadJobs().catch(() => renderJobList([]));
attachFrenchValidation();
