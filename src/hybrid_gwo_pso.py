"""
src/hybrid_gwo_pso.py
Hybrid Grey Wolf - Particle Swarm Optimization (Hybrid GWO-PSO)
for Renewable Microgrid Load Dispatch.
Integrates GWO multi-leader exploration with PSO velocity exploitation
and Deb's feasibility rules for robust constraint satisfaction.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, List, Callable
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def is_better(res_new: Dict[str, Any], res_curr: Dict[str, Any]) -> bool:
    """
    Deb's feasibility rule for comparing two candidate solutions:
    1. Feasible is strictly preferred over infeasible.
    2. Between two feasible solutions, lower operating cost wins.
    3. Between two infeasible solutions, lower penalty / fitness wins.
    """
    if not res_curr:
        return True
    feas_new = res_new.get("is_feasible", False)
    feas_curr = res_curr.get("is_feasible", False)

    if feas_new and not feas_curr:
        return True
    elif not feas_new and feas_curr:
        return False
    elif feas_new and feas_curr:
        return res_new["operating_cost"] < res_curr["operating_cost"]
    else:
        return res_new["fitness"] < res_curr["fitness"]


class HybridGWOPSO:
    """
    Synergistic Hybrid Grey Wolf - Particle Swarm Optimizer.
    Blends GWO Alpha/Beta/Delta hunting leadership with PSO velocity-based
    memory updates via an adaptive time-varying blending schedule.
    """

    def __init__(
        self,
        objective_evaluator: Callable[[np.ndarray], Dict[str, Any]],
        lower_bounds: np.ndarray,
        upper_bounds: np.ndarray,
        pop_size: int = 30,
        max_iter: int = 100,
        w_max: float = 0.9,
        w_min: float = 0.4,
        c1: float = 1.5,
        c2: float = 1.5,
        lambda_initial: float = 0.80,
        lambda_final: float = 0.20,
        v_max_ratio: float = 0.20,
        seed: Optional[int] = None
    ):
        self.objective_evaluator = objective_evaluator
        self.lb = np.array(lower_bounds, dtype=np.float64)
        self.ub = np.array(upper_bounds, dtype=np.float64)
        self.dim = len(self.lb)
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w_max = w_max
        self.w_min = w_min
        self.c1 = c1
        self.c2 = c2
        self.lambda_initial = lambda_initial
        self.lambda_final = lambda_final
        self.v_max = v_max_ratio * (self.ub - self.lb)
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # GWO hierarchy (Alpha = 1st, Beta = 2nd, Delta = 3rd)
        self.alpha_pos = np.zeros(self.dim, dtype=np.float64)
        self.alpha_score = np.inf
        self.alpha_details: Dict[str, Any] = {}

        self.beta_pos = np.zeros(self.dim, dtype=np.float64)
        self.beta_score = np.inf
        self.beta_details: Dict[str, Any] = {}

        self.delta_pos = np.zeros(self.dim, dtype=np.float64)
        self.delta_score = np.inf
        self.delta_details: Dict[str, Any] = {}

        # PSO vectors
        self.positions = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.velocities = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.pbest_positions = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.pbest_details: List[Dict[str, Any]] = [{} for _ in range(self.pop_size)]

        self.convergence_curve: List[float] = []
        self.execution_time: float = 0.0

    def _update_hierarchy(self, pos: np.ndarray, res: Dict[str, Any]):
        """Updates pack leadership Alpha, Beta, Delta according to Deb's rules."""
        if is_better(res, self.alpha_details):
            self.delta_details = self.beta_details
            self.delta_pos = self.beta_pos.copy()
            self.delta_score = self.beta_score

            self.beta_details = self.alpha_details
            self.beta_pos = self.alpha_pos.copy()
            self.beta_score = self.alpha_score

            self.alpha_details = res
            self.alpha_pos = pos.copy()
            self.alpha_score = res["fitness"]

        elif is_better(res, self.beta_details):
            self.delta_details = self.beta_details
            self.delta_pos = self.beta_pos.copy()
            self.delta_score = self.beta_score

            self.beta_details = res
            self.beta_pos = pos.copy()
            self.beta_score = res["fitness"]

        elif is_better(res, self.delta_details):
            self.delta_details = res
            self.delta_pos = pos.copy()
            self.delta_score = res["fitness"]

    def initialize_population(self):
        """Initializes population uniformly, evaluates candidates, and sets initial leaders."""
        for i in range(self.pop_size):
            self.positions[i] = self.lb + self.rng.random(self.dim) * (self.ub - self.lb)
            self.velocities[i] = (self.rng.random(self.dim) - 0.5) * 2.0 * self.v_max
            eval_res = self.objective_evaluator(self.positions[i])

            self.pbest_positions[i] = self.positions[i].copy()
            self.pbest_details[i] = eval_res

            self._update_hierarchy(self.positions[i], eval_res)

    def optimize(self) -> Dict[str, Any]:
        """
        Executes the Hybrid GWO-PSO optimization pipeline.
        Returns convergence curve, best dispatch schedule, and comparative metrics.
        """
        start_time = time.perf_counter()
        self.initialize_population()
        self.convergence_curve = [self.alpha_details.get("operating_cost", self.alpha_score)]

        for it in range(1, self.max_iter + 1):
            # Dynamic coefficients
            # GWO exploration coefficient a (2.0 -> 0.0)
            a = 2.0 - (it / self.max_iter) * 2.0
            # PSO inertia weight w (0.9 -> 0.4)
            w = self.w_max - (it / self.max_iter) * (self.w_max - self.w_min)
            # Adaptive hybrid blending weight lambda (0.8 -> 0.2)
            lambda_t = self.lambda_initial - (it / self.max_iter) * (self.lambda_initial - self.lambda_final)

            for i in range(self.pop_size):
                # 1. GWO Encircling & Hunting Vector
                r1_a = self.rng.random(self.dim)
                r2_a = self.rng.random(self.dim)
                A1 = 2.0 * a * r1_a - a
                C1 = 2.0 * r2_a
                D_alpha = np.abs(C1 * self.alpha_pos - self.positions[i])
                X1 = self.alpha_pos - A1 * D_alpha

                r1_b = self.rng.random(self.dim)
                r2_b = self.rng.random(self.dim)
                A2 = 2.0 * a * r1_b - a
                C2 = 2.0 * r2_b
                D_beta = np.abs(C2 * self.beta_pos - self.positions[i])
                X2 = self.beta_pos - A2 * D_beta

                r1_d = self.rng.random(self.dim)
                r2_d = self.rng.random(self.dim)
                A3 = 2.0 * a * r1_d - a
                C3 = 2.0 * r2_d
                D_delta = np.abs(C3 * self.delta_pos - self.positions[i])
                X3 = self.delta_pos - A3 * D_delta

                x_gwo = (X1 + X2 + X3) / 3.0

                # 2. PSO Velocity Vector guided by Personal Best and Global Best Alpha
                r1_p = self.rng.random(self.dim)
                r2_p = self.rng.random(self.dim)
                cog_vel = self.c1 * r1_p * (self.pbest_positions[i] - self.positions[i])
                soc_vel = self.c2 * r2_p * (self.alpha_pos - self.positions[i])
                self.velocities[i] = w * self.velocities[i] + cog_vel + soc_vel
                self.velocities[i] = np.clip(self.velocities[i], -self.v_max, self.v_max)

                # 3. Adaptive Hybrid Position Update
                x_pso = self.positions[i] + self.velocities[i]
                new_pos = lambda_t * x_gwo + (1.0 - lambda_t) * x_pso

                # Boundary clamping
                new_pos = np.clip(new_pos, self.lb, self.ub)
                self.positions[i] = new_pos

                # 4. Evaluation
                eval_res = self.objective_evaluator(self.positions[i])

                # Update Personal Best
                if is_better(eval_res, self.pbest_details[i]):
                    self.pbest_details[i] = eval_res
                    self.pbest_positions[i] = self.positions[i].copy()

                # Update Pack Hierarchy (Alpha, Beta, Delta)
                self._update_hierarchy(self.positions[i], eval_res)

            best_val = self.alpha_details.get("operating_cost", self.alpha_score)
            self.convergence_curve.append(best_val)

        self.execution_time = time.perf_counter() - start_time
        logger.info(
            f"Hybrid GWO-PSO completed in {self.execution_time:.3f}s. "
            f"Alpha Cost: ${self.alpha_details.get('operating_cost', self.alpha_score):.2f}"
        )

        return {
            "algorithm": "Hybrid GWO-PSO",
            "best_fitness": self.alpha_score,
            "best_operating_cost": self.alpha_details.get("operating_cost", self.alpha_score),
            "best_position": self.alpha_pos,
            "best_details": self.alpha_details,
            "convergence_curve": self.convergence_curve,
            "execution_time": self.execution_time,
            "iterations": self.max_iter,
            "pop_size": self.pop_size
        }
