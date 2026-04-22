from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Tuple

from app.embedding_client import EmbeddingClient, fuzzy_token_overlap, normalize_text
from app.models import (
    CandidateProfile,
    CompatibilityPenalty,
    CompatibilityResponse,
    CriterionScore,
    JobProfile,
    PairCompatibility,
    SkillEntry,
)


CRITERION_WEIGHTS = {
    "location": 0.1,
    "contract": 0.08,
    "salary": 0.08,
    "experience": 0.12,
    "required_skills": 0.2,
    "desired_skills": 0.1,
    "role_alignment": 0.12,
    "motivation": 0.1,
    "culture": 0.05,
    "learning_potential": 0.05,
}


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def list_to_text(values: Iterable[str]) -> str:
    return ", ".join(value.strip() for value in values if value and value.strip())


class CompatibilityScorer:
    def __init__(self, embedding_client: EmbeddingClient | None = None) -> None:
        self.embedding_client = embedding_client or EmbeddingClient()

    def score_all(
        self,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        top_k_per_candidate: int,
    ) -> CompatibilityResponse:
        results: List[PairCompatibility] = []

        for candidate in candidates:
            candidate_results = [self.score_pair(candidate, job) for job in jobs]
            candidate_results.sort(key=lambda item: item.overall_score, reverse=True)
            results.extend(candidate_results[:top_k_per_candidate])

        results.sort(key=lambda item: (item.candidate_name.lower(), -item.overall_score, item.job_title.lower()))
        return CompatibilityResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            embedding_mode="remote" if self.embedding_client.mode() == "remote" else "fallback",
            embedding_model=self.embedding_client.model,
            results=results,
        )

    def score_pair(self, candidate: CandidateProfile, job: JobProfile) -> PairCompatibility:
        criteria = [
            self._score_location(candidate, job),
            self._score_contract(candidate, job),
            self._score_salary(candidate, job),
            self._score_experience(candidate, job),
            self._score_required_skills(candidate, job),
            self._score_desired_skills(candidate, job),
            self._score_role_alignment(candidate, job),
            self._score_motivation(candidate, job),
            self._score_culture(candidate, job),
            self._score_learning_potential(candidate, job),
        ]

        base_score = sum(item.weighted_score for item in criteria)
        penalties = self._compute_penalties(criteria)
        final_score = base_score
        for penalty in penalties:
            final_score *= penalty.factor

        summary = self._build_summary(criteria, penalties)
        return PairCompatibility(
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            job_id=job.id,
            job_title=job.title,
            overall_score=clamp_score(final_score),
            base_score=round(base_score, 2),
            criteria=criteria,
            penalties=penalties,
            summary=summary,
        )

    def _criterion(
        self,
        key: str,
        label: str,
        score: float,
        source: str,
        explanation: str,
    ) -> CriterionScore:
        weight = CRITERION_WEIGHTS[key]
        normalized_score = clamp_score(score)
        return CriterionScore(
            key=key,
            label=label,
            score=normalized_score,
            weight=weight,
            weighted_score=round(normalized_score * weight, 2),
            source=source,  # type: ignore[arg-type]
            explanation=explanation,
        )

    def _score_location(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        same_city = normalize_text(candidate.location.city) == normalize_text(job.location.city)
        same_country = normalize_text(candidate.location.country) == normalize_text(job.location.country)
        candidate_pref = candidate.location.remote_preference
        job_mode = job.location.work_mode

        if job_mode == "remote":
            score = 100 if candidate_pref in {"remote", "hybrid"} else 80
            explanation = "Le poste est remote, la contrainte géographique est faible."
        elif same_city:
            score = 100 if job_mode != "hybrid" or candidate_pref != "remote" else 90
            explanation = "Le candidat et le poste sont dans la même ville."
        elif job_mode == "hybrid":
            if same_country and candidate.location.mobility_km >= 20:
                score = 60
                explanation = "Ville différente mais un poste hybride reste envisageable avec mobilité."
            else:
                score = 35
                explanation = "Le poste est hybride dans une autre ville, la mobilité semble limitée."
        else:
            if same_country and candidate.location.mobility_km >= 50:
                score = 40
                explanation = "Le poste est sur site dans une autre ville, la mobilité compense partiellement."
            else:
                score = 0
                explanation = "Le poste est sur site dans une autre ville sans mobilité suffisante."

        return self._criterion("location", "Compatibilité géographique", score, "structured", explanation)

    def _score_contract(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        preferred_contracts = set(candidate.preferences.contract_types)
        if not preferred_contracts:
            return self._criterion(
                "contract",
                "Compatibilité contrat",
                70,
                "structured",
                "Aucune préférence de contrat renseignée, score neutre.",
            )

        if job.conditions.contract_type in preferred_contracts:
            score = 100
            explanation = f"Le contrat {job.conditions.contract_type.upper()} fait partie des préférences."
        else:
            score = 20
            explanation = f"Le contrat {job.conditions.contract_type.upper()} ne correspond pas aux préférences."
        return self._criterion("contract", "Compatibilité contrat", score, "structured", explanation)

    def _score_salary(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        expected_min = candidate.preferences.salary_min
        job_min = job.conditions.salary_min
        job_max = job.conditions.salary_max

        if expected_min is None or (job_min is None and job_max is None):
            return self._criterion(
                "salary",
                "Compatibilité salariale",
                70,
                "structured",
                "Informations salariales incomplètes, score neutre.",
            )

        available_salary = job_max if job_max is not None else job_min
        if available_salary is None:
            score = 70
            explanation = "Salaire poste non renseigné."
        elif available_salary >= expected_min:
            score = 100
            explanation = "La fourchette salariale couvre l'attente minimale du candidat."
        else:
            score = max(0, min(100, round((available_salary / expected_min) * 100)))
            explanation = "La rémunération proposée est inférieure à l'attente minimale du candidat."
        return self._criterion("salary", "Compatibilité salariale", score, "structured", explanation)

    def _score_experience(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        required_years = job.requirements.minimum_years_experience
        if required_years <= 0:
            return self._criterion(
                "experience",
                "Compatibilité expérience",
                100,
                "structured",
                "Aucun minimum d'expérience n'est demandé.",
            )

        if candidate.years_experience >= required_years:
            score = 100
            explanation = "Le candidat satisfait le minimum d'expérience demandé."
        else:
            score = ((candidate.years_experience + 1) / (required_years + 1)) * 100
            explanation = "Le candidat n'atteint pas encore complètement le niveau d'expérience requis."
        return self._criterion("experience", "Compatibilité expérience", score, "structured", explanation)

    def _score_required_skills(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        required_skills = [skill for skill in job.requirements.mandatory_skills if skill.strip()]
        if not required_skills:
            return self._criterion(
                "required_skills",
                "Compétences obligatoires",
                100,
                "structured",
                "Le poste ne définit pas de compétences obligatoires.",
            )

        candidate_skill_names = [skill.name for skill in candidate.skills]
        exact_matches = sum(1 for skill in required_skills if self._has_skill(candidate_skill_names, skill))
        exact_ratio = exact_matches / len(required_skills)
        semantic_score, source = self._semantic_similarity(list_to_text(required_skills), list_to_text(candidate_skill_names))
        score = 100 * ((0.65 * exact_ratio) + (0.35 * semantic_score))
        explanation = f"{exact_matches} compétence(s) obligatoire(s) retrouvée(s) exactement sur {len(required_skills)}."
        return self._criterion("required_skills", "Compétences obligatoires", score, self._hybrid_source(source), explanation)

    def _score_desired_skills(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        desired_skills = [skill for skill in job.desired_skills if skill.name.strip()]
        if not desired_skills:
            return self._criterion(
                "desired_skills",
                "Compétences souhaitées",
                70,
                "structured",
                "Le poste ne précise pas de compétences bonus.",
            )

        level_ratio = self._desired_skill_level_ratio(candidate.skills, desired_skills)
        semantic_score, source = self._semantic_similarity(
            list_to_text(skill.name for skill in desired_skills),
            list_to_text(skill.name for skill in candidate.skills),
        )
        score = 100 * ((0.6 * level_ratio) + (0.4 * semantic_score))
        explanation = "Le score combine la couverture des compétences bonus et leur proximité sémantique."
        return self._criterion("desired_skills", "Compétences souhaitées", score, self._hybrid_source(source), explanation)

    def _score_role_alignment(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        role_terms = [candidate.current_title or "", *candidate.preferences.target_roles]
        candidate_text = " ".join(
            [
                *role_terms,
                list_to_text(candidate.preferences.target_sectors),
            ]
        )
        job_text = " ".join([job.title, job.team or "", job.missions])
        semantic_score, source = self._semantic_similarity(candidate_text, job_text)
        title_alignment = max((self._phrase_match_score(term, job.title) for term in role_terms if term.strip()), default=0.0)
        mission_alignment = self._phrase_match_score(
            list_to_text(candidate.motivation.mission_preferences),
            job.missions,
        )
        score = 100 * ((0.5 * title_alignment) + (0.2 * mission_alignment) + (0.3 * semantic_score))
        explanation = "Alignement entre le parcours visé par le candidat et l'intitulé/missions du poste."
        return self._criterion("role_alignment", "Alignement du poste", score, self._hybrid_source(source), explanation)

    def _score_motivation(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        candidate_text = " ".join(
            [
                candidate.motivation.free_text,
                list_to_text(candidate.motivation.mission_preferences),
            ]
        )
        job_text = " ".join([job.missions, job.target_profile.growth_potential])
        semantic_score, source = self._semantic_similarity(candidate_text, job_text)
        missions_overlap = self._phrase_match_score(
            list_to_text(candidate.motivation.mission_preferences),
            job.missions,
        )
        drivers_overlap = self._phrase_match_score(
            list_to_text(candidate.motivation.drivers),
            " ".join([job.missions, list_to_text(job.environment.culture_keywords)]),
        )
        raw_score = (0.65 * semantic_score) + (0.2 * missions_overlap) + (0.15 * drivers_overlap)
        score = self._soft_textual_score(raw_score, floor=28)
        explanation = "Proximité entre la formulation de la motivation et les missions proposées."
        return self._criterion("motivation", "Motivation", score, self._hybrid_source(source), explanation)

    def _score_culture(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        candidate_text = " ".join(
            [
                list_to_text(candidate.preferences.values),
                list_to_text(candidate.motivation.drivers),
            ]
        )
        job_text = " ".join(
            [
                list_to_text(job.environment.culture_keywords),
                list_to_text(job.target_profile.expected_traits),
                job.environment.team_style,
            ]
        )
        semantic_score, source = self._semantic_similarity(candidate_text, job_text)
        values_overlap = self._phrase_match_score(
            " ".join([list_to_text(candidate.preferences.values), list_to_text(candidate.motivation.drivers)]),
            " ".join(
                [
                    list_to_text(job.environment.culture_keywords),
                    list_to_text(job.target_profile.expected_traits),
                    job.environment.team_style,
                ]
            ),
        )
        raw_score = (0.55 * semantic_score) + (0.45 * values_overlap)
        score = self._soft_textual_score(raw_score, floor=22)
        explanation = "Compatibilité entre les valeurs du candidat et la culture/les traits attendus."
        return self._criterion("culture", "Culture et valeurs", score, self._hybrid_source(source), explanation)

    def _score_learning_potential(self, candidate: CandidateProfile, job: JobProfile) -> CriterionScore:
        candidate_text = " ".join(
            [
                list_to_text(candidate.potential.learning_goals),
                list_to_text(candidate.potential.growth_domains),
                candidate.potential.transferable_experiences,
            ]
        )
        job_text = " ".join(
            [
                list_to_text(skill.name for skill in job.desired_skills),
                list_to_text(job.target_profile.learning_expectations),
                job.target_profile.growth_potential,
            ]
        )
        semantic_score, source = self._semantic_similarity(candidate_text, job_text)
        growth_overlap = self._phrase_match_score(
            " ".join([list_to_text(candidate.potential.learning_goals), list_to_text(candidate.potential.growth_domains)]),
            " ".join([list_to_text(job.target_profile.learning_expectations), job.target_profile.growth_potential]),
        )
        raw_score = (0.7 * semantic_score) + (0.3 * growth_overlap)
        score = self._soft_textual_score(raw_score, floor=24)
        explanation = "Potentiel d'apprentissage estimé à partir des objectifs de progression et du profil recherché."
        return self._criterion("learning_potential", "Potentiel d'apprentissage", score, self._hybrid_source(source), explanation)

    def _compute_penalties(self, criteria: Sequence[CriterionScore]) -> List[CompatibilityPenalty]:
        penalties: List[CompatibilityPenalty] = []
        lookup = {criterion.key: criterion for criterion in criteria}

        if lookup["location"].score == 0:
            penalties.append(
                CompatibilityPenalty(label="Localisation bloquante pour ce poste", factor=0.65)
            )
        if lookup["required_skills"].score < 45:
            penalties.append(
                CompatibilityPenalty(label="Couverture insuffisante des compétences obligatoires", factor=0.8)
            )
        if lookup["contract"].score < 40:
            penalties.append(
                CompatibilityPenalty(label="Type de contrat peu compatible", factor=0.9)
            )
        return penalties

    def _build_summary(
        self,
        criteria: Sequence[CriterionScore],
        penalties: Sequence[CompatibilityPenalty],
    ) -> str:
        top_criteria = sorted(criteria, key=lambda item: item.score, reverse=True)[:2]
        low_criteria = sorted(criteria, key=lambda item: item.score)[:2]
        strengths = ", ".join(f"{item.label.lower()} ({item.score}%)" for item in top_criteria)
        weaknesses = ", ".join(f"{item.label.lower()} ({item.score}%)" for item in low_criteria)
        if penalties:
            penalty_text = "; pénalités : " + ", ".join(penalty.label for penalty in penalties)
        else:
            penalty_text = ""
        return f"Points forts : {strengths}. Points de vigilance : {weaknesses}{penalty_text}."

    def _desired_skill_level_ratio(
        self,
        candidate_skills: Sequence[SkillEntry],
        desired_skills: Sequence[SkillEntry],
    ) -> float:
        if not desired_skills:
            return 1.0

        candidate_lookup = {normalize_text(skill.name): skill.level for skill in candidate_skills if skill.name.strip()}
        total_weight = sum(skill.level for skill in desired_skills)
        if total_weight == 0:
            return 0.0

        accumulated = 0.0
        for desired in desired_skills:
            candidate_level = candidate_lookup.get(normalize_text(desired.name), 0)
            coverage = min(candidate_level / desired.level, 1.0) if desired.level else 0.0
            accumulated += coverage * desired.level
        return accumulated / total_weight

    def _has_skill(self, candidate_skill_names: Sequence[str], expected_skill: str) -> bool:
        normalized_expected = normalize_text(expected_skill)
        return any(normalize_text(skill_name) == normalized_expected for skill_name in candidate_skill_names)

    def _semantic_similarity(self, left: str, right: str) -> Tuple[float, str]:
        score, source = self.embedding_client.similarity(left, right)
        return max(0.0, min(1.0, score)), source

    def _hybrid_source(self, source: str) -> str:
        return "hybrid" if source == "embedding" else "lexical_fallback"

    def _phrase_match_score(self, left: str, right: str) -> float:
        normalized_left = normalize_text(left)
        normalized_right = normalize_text(right)
        if not normalized_left or not normalized_right:
            return 0.0
        if normalized_left in normalized_right or normalized_right in normalized_left:
            return 1.0
        return fuzzy_token_overlap(normalized_left, normalized_right)

    def _soft_textual_score(self, raw_score: float, floor: int) -> float:
        bounded = max(0.0, min(1.0, raw_score))
        return floor + ((100 - floor) * bounded)
