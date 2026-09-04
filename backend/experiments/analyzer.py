"""Statistical analysis for recovery-agent experiments."""

from __future__ import annotations

import math

from scipy.stats import chisquare
from statsmodels.stats.proportion import proportions_ztest


class ExperimentAnalyzer:
    """Calculate sample-ratio and recovery-lift metrics for one experiment."""

    def analyze(
        self,
        experiment_id: str,
        control_recovered: int,
        control_total: int,
        variant_recovered: int,
        variant_total: int,
    ) -> dict:
        self._validate_counts(
            control_recovered, control_total, variant_recovered, variant_total
        )

        total = control_total + variant_total
        control_rate = control_recovered / control_total if control_total else 0.0
        variant_rate = variant_recovered / variant_total if variant_total else 0.0
        absolute_lift = variant_rate - control_rate
        relative_lift = absolute_lift / control_rate if control_rate else 0.0

        srm_chi_square, srm_p_value = self._sample_ratio_metrics(
            control_total, variant_total
        )
        z_stat, p_value = self._recovery_test(
            control_recovered, control_total, variant_recovered, variant_total
        )
        standard_error = self._standard_error(
            control_rate, control_total, variant_rate, variant_total
        )
        ci_lower = absolute_lift - 1.96 * standard_error
        ci_upper = absolute_lift + 1.96 * standard_error

        return {
            "experiment_id": experiment_id,
            "control": {
                "recovered": control_recovered,
                "total": control_total,
                "recovery_rate": control_rate,
            },
            "variant": {
                "recovered": variant_recovered,
                "total": variant_total,
                "recovery_rate": variant_rate,
            },
            "sample_size": total,
            "sample_size_control": control_total,
            "sample_size_variant": variant_total,
            "control_rate": control_rate,
            "variant_rate": variant_rate,
            "absolute_lift": absolute_lift,
            "relative_lift": relative_lift,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "z_statistic": z_stat,
            "p_value": p_value,
            "is_significant": p_value < 0.05 and absolute_lift > 0,
            "srm": {
                "chi_square": srm_chi_square,
                "p_value": srm_p_value,
                "pass": srm_p_value > 0.01,
            },
            "srm_pass": srm_p_value > 0.01,
        }

    @staticmethod
    def _validate_counts(
        control_recovered: int,
        control_total: int,
        variant_recovered: int,
        variant_total: int,
    ) -> None:
        values = (control_recovered, control_total, variant_recovered, variant_total)
        if any(not isinstance(value, int) or value < 0 for value in values):
            raise ValueError("Experiment counts must be non-negative integers")
        if control_recovered > control_total or variant_recovered > variant_total:
            raise ValueError("Recovered counts cannot exceed total counts")

    @staticmethod
    def _sample_ratio_metrics(control_total: int, variant_total: int) -> tuple[float, float]:
        total = control_total + variant_total
        if total == 0:
            return 0.0, 1.0
        result = chisquare(
            [control_total, variant_total],
            f_exp=[total * 0.8, total * 0.2],
        )
        return float(result.statistic), float(result.pvalue)

    @staticmethod
    def _recovery_test(
        control_recovered: int,
        control_total: int,
        variant_recovered: int,
        variant_total: int,
    ) -> tuple[float, float]:
        if control_total == 0 or variant_total == 0:
            return 0.0, 1.0
        z_stat, p_value = proportions_ztest(
            [variant_recovered, control_recovered],
            [variant_total, control_total],
            alternative="larger",
        )
        return float(z_stat), float(p_value)

    @staticmethod
    def _standard_error(
        control_rate: float,
        control_total: int,
        variant_rate: float,
        variant_total: int,
    ) -> float:
        if control_total == 0 or variant_total == 0:
            return 0.0
        return math.sqrt(
            control_rate * (1 - control_rate) / control_total
            + variant_rate * (1 - variant_rate) / variant_total
        )
