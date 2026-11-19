"""
src/pso.py
Standalone Particle Swarm Optimization (PSO) implemented from scratch
for renewable microgrid load dispatch.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, List, Callable
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ParticleSwarmOptimizer:
    """
    Standard Particle Swarm Optimizer with dynamic inertia weight,
    velocity clamping, boundary repair, and convergence tracking.
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
        c1: float = 1.8,
        c2: float = 1.8,
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
        self.v_max = v_max_ratio * (self.ub - self.lb)
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Internal state
        self.positions = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.velocities = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.pbest_positions = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.pbest_fitness = np.full(self.pop_size, np.inf, dtype=np.float64)
        self.gbest_position = np.zeros(self.dim, dtype=np.float64)
        self.gbest_fitness = np.inf
        self.gbest_details: Dict[str, Any] = {}
        self.convergence_curve: List[float] = []
        self.execution_time: float = 0.0

    def initialize_population(self):
        """Initializes particle positions uniformly within bounds and velocities to zero or small random."""
        for i in range(self.pop_size):
            self.positions[i] = self.lb + self.rng.random(self.dim) * (self.ub - self.lb)
            self.velocities[i] = (self.rng.random(self.dim) - 0.5) * 2.0 * self.v_max
            eval_res = self.objective_evaluator(self.positions[i])
            fit = eval_res["fitness"]
            self.pbest_positions[i] = self.positions[i].copy()
            self.pbest_fitness[i] = fit

            if fit < self.gbest_fitness:
                self.gbest_fitness = fit
                self.gbest_position = self.positions[i].copy()
                self.gbest_details = eval_res

    def optimize(self) -> Dict[str, Any]:
        """
        Executes PSO optimization over max_iter iterations.
        Returns detailed results including convergence history, best solution, and metrics.
        """
        start_time = time.perf_counter()
        self.initialize_population()
        self.convergence_curve = [self.gbest_fitness]

        for it in range(1, self.max_iter + 1):
            # Linearly decreasing inertia weight
            w = self.w_max - (it / self.max_iter) * (self.w_max - self.w_min)

            for i in range(self.pop_size):
                r1 = self.rng.random(self.dim)
                r2 = self.rng.random(self.dim)

                # Velocity update
                cog_vel = self.c1 * r1 * (self.pbest_positions[i] - self.positions[i])
                soc_vel = self.c2 * r2 * (self.gbest_position - self.positions[i])
                self.velocities[i] = w * self.velocities[i] + cog_vel + soc_vel

                # Velocity clamping
                self.velocities[i] = np.clip(self.velocities[i], -self.v_max, self.v_max)

                # Position update
                self.positions[i] = self.positions[i] + self.velocities[i]

                # Boundary clamping
                self.positions[i] = np.clip(self.positions[i], self.lb, self.ub)

                # Fitness evaluation
                eval_res = self.objective_evaluator(self.positions[i])
                fit = eval_res["fitness"]

                # Update personal best
                if fit < self.pbest_fitness[i]:
                    self.pbest_fitness[i] = fit
                    self.pbest_positions[i] = self.positions[i].copy()

                    # Update global best
                    if fit < self.gbest_fitness:
                        self.gbest_fitness = fit
                        self.gbest_position = self.positions[i].copy()
                        self.gbest_details = eval_res

            self.convergence_curve.append(self.gbest_fitness)

        self.execution_time = time.perf_counter() - start_time
        logger.info(
            f"PSO completed in {self.execution_time:.3f}s. "
            f"Best Fitness: ${self.gbest_fitness:.2f}"
        )

        return {
            "algorithm": "PSO",
            "best_fitness": self.gbest_fitness,
            "best_position": self.gbest_position,
            "best_details": self.gbest_details,
            "convergence_curve": self.convergence_curve,
            "execution_time": self.execution_time,
            "iterations": self.max_iter,
            "pop_size": self.pop_size
        }
