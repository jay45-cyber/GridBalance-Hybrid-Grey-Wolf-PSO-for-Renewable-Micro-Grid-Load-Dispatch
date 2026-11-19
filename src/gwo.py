"""
src/gwo.py
Standalone Grey Wolf Optimizer (GWO) implemented from scratch
for renewable microgrid load dispatch.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, List, Callable
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GreyWolfOptimizer:
    """
    Standard Grey Wolf Optimizer (Mirjalili et al., 2014) with Alpha, Beta, Delta
    pack leadership, encircling, hunting, and boundary repair.
    """

    def __init__(
        self,
        objective_evaluator: Callable[[np.ndarray], Dict[str, Any]],
        lower_bounds: np.ndarray,
        upper_bounds: np.ndarray,
        pop_size: int = 30,
        max_iter: int = 100,
        a_initial: float = 2.0,
        a_final: float = 0.0,
        seed: Optional[int] = None
    ):
        self.objective_evaluator = objective_evaluator
        self.lb = np.array(lower_bounds, dtype=np.float64)
        self.ub = np.array(upper_bounds, dtype=np.float64)
        self.dim = len(self.lb)
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.a_initial = a_initial
        self.a_final = a_final
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Pack hierarchy
        self.alpha_pos = np.zeros(self.dim, dtype=np.float64)
        self.alpha_score = np.inf
        self.alpha_details: Dict[str, Any] = {}

        self.beta_pos = np.zeros(self.dim, dtype=np.float64)
        self.beta_score = np.inf
        self.beta_details: Dict[str, Any] = {}

        self.delta_pos = np.zeros(self.dim, dtype=np.float64)
        self.delta_score = np.inf
        self.delta_details: Dict[str, Any] = {}

        self.positions = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.convergence_curve: List[float] = []
        self.execution_time: float = 0.0

    def initialize_population(self):
        """Initializes the wolf pack uniformly within search bounds and determines Alpha, Beta, Delta."""
        for i in range(self.pop_size):
            self.positions[i] = self.lb + self.rng.random(self.dim) * (self.ub - self.lb)
            eval_res = self.objective_evaluator(self.positions[i])
            fit = eval_res["fitness"]

            if fit < self.alpha_score:
                self.delta_score = self.beta_score
                self.delta_pos = self.beta_pos.copy()
                self.delta_details = self.beta_details

                self.beta_score = self.alpha_score
                self.beta_pos = self.alpha_pos.copy()
                self.beta_details = self.alpha_details

                self.alpha_score = fit
                self.alpha_pos = self.positions[i].copy()
                self.alpha_details = eval_res

            elif fit < self.beta_score:
                self.delta_score = self.beta_score
                self.delta_pos = self.beta_pos.copy()
                self.delta_details = self.beta_details

                self.beta_score = fit
                self.beta_pos = self.positions[i].copy()
                self.beta_details = eval_res

            elif fit < self.delta_score:
                self.delta_score = fit
                self.delta_pos = self.positions[i].copy()
                self.delta_details = eval_res

    def optimize(self) -> Dict[str, Any]:
        """
        Executes GWO optimization over max_iter iterations.
        Returns detailed results including convergence curve, alpha solution, and metrics.
        """
        start_time = time.perf_counter()
        self.initialize_population()
        self.convergence_curve = [self.alpha_score]

        for it in range(1, self.max_iter + 1):
            # Linearly decreasing exploration coefficient a from a_initial to a_final
            a = self.a_initial - (it / self.max_iter) * (self.a_initial - self.a_final)

            for i in range(self.pop_size):
                # Alpha encircling & hunting
                r1_a = self.rng.random(self.dim)
                r2_a = self.rng.random(self.dim)
                A1 = 2.0 * a * r1_a - a
                C1 = 2.0 * r2_a
                D_alpha = np.abs(C1 * self.alpha_pos - self.positions[i])
                X1 = self.alpha_pos - A1 * D_alpha

                # Beta encircling & hunting
                r1_b = self.rng.random(self.dim)
                r2_b = self.rng.random(self.dim)
                A2 = 2.0 * a * r1_b - a
                C2 = 2.0 * r2_b
                D_beta = np.abs(C2 * self.beta_pos - self.positions[i])
                X2 = self.beta_pos - A2 * D_beta

                # Delta encircling & hunting
                r1_d = self.rng.random(self.dim)
                r2_d = self.rng.random(self.dim)
                A3 = 2.0 * a * r1_d - a
                C3 = 2.0 * r2_d
                D_delta = np.abs(C3 * self.delta_pos - self.positions[i])
                X3 = self.delta_pos - A3 * D_delta

                # Updated position is the centroid of leadership positions
                new_pos = (X1 + X2 + X3) / 3.0

                # Boundary clamping
                new_pos = np.clip(new_pos, self.lb, self.ub)
                self.positions[i] = new_pos

                # Evaluation
                eval_res = self.objective_evaluator(self.positions[i])
                fit = eval_res["fitness"]

                # Hierarchy update
                if fit < self.alpha_score:
                    self.delta_score = self.beta_score
                    self.delta_pos = self.beta_pos.copy()
                    self.delta_details = self.beta_details

                    self.beta_score = self.alpha_score
                    self.beta_pos = self.alpha_pos.copy()
                    self.beta_details = self.alpha_details

                    self.alpha_score = fit
                    self.alpha_pos = self.positions[i].copy()
                    self.alpha_details = eval_res

                elif fit < self.beta_score:
                    self.delta_score = self.beta_score
                    self.delta_pos = self.beta_pos.copy()
                    self.delta_details = self.beta_details

                    self.beta_score = fit
                    self.beta_pos = self.positions[i].copy()
                    self.beta_details = eval_res

                elif fit < self.delta_score:
                    self.delta_score = fit
                    self.delta_pos = self.positions[i].copy()
                    self.delta_details = eval_res

            self.convergence_curve.append(self.alpha_score)

        self.execution_time = time.perf_counter() - start_time
        logger.info(
            f"GWO completed in {self.execution_time:.3f}s. "
            f"Alpha Fitness: ${self.alpha_score:.2f}"
        )

        return {
            "algorithm": "GWO",
            "best_fitness": self.alpha_score,
            "best_position": self.alpha_pos,
            "best_details": self.alpha_details,
            "convergence_curve": self.convergence_curve,
            "execution_time": self.execution_time,
            "iterations": self.max_iter,
            "pop_size": self.pop_size
        }
