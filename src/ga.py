"""
src/ga.py
Standalone Real-Coded Genetic Algorithm (GA) implemented from scratch
for renewable microgrid load dispatch with Deb's feasibility rules.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, List, Callable
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def is_better(res_new: Dict[str, Any], res_curr: Dict[str, Any]) -> bool:
    """Deb's feasibility rule for comparing two candidate solutions."""
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


class GeneticAlgorithm:
    """
    Real-Coded Genetic Algorithm with Tournament Selection,
    Arithmetic Crossover, Gaussian Mutation, Elitism, and Deb's feasibility rules.
    """

    def __init__(
        self,
        objective_evaluator: Callable[[np.ndarray], Dict[str, Any]],
        lower_bounds: np.ndarray,
        upper_bounds: np.ndarray,
        pop_size: int = 30,
        max_iter: int = 100,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.15,
        tournament_size: int = 3,
        elite_count: int = 2,
        seed: Optional[int] = None
    ):
        self.objective_evaluator = objective_evaluator
        self.lb = np.array(lower_bounds, dtype=np.float64)
        self.ub = np.array(upper_bounds, dtype=np.float64)
        self.dim = len(self.lb)
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.elite_count = elite_count
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.population = np.zeros((self.pop_size, self.dim), dtype=np.float64)
        self.fitness = np.full(self.pop_size, np.inf, dtype=np.float64)
        self.eval_details: List[Dict[str, Any]] = [{} for _ in range(self.pop_size)]

        self.best_position = np.zeros(self.dim, dtype=np.float64)
        self.best_fitness = np.inf
        self.best_details: Dict[str, Any] = {}
        self.convergence_curve: List[float] = []
        self.execution_time: float = 0.0

    def initialize_population(self):
        """Initializes population uniformly within bounds and evaluates initial fitness."""
        for i in range(self.pop_size):
            self.population[i] = self.lb + self.rng.random(self.dim) * (self.ub - self.lb)
            res = self.objective_evaluator(self.population[i])
            self.fitness[i] = res["fitness"]
            self.eval_details[i] = res

            if is_better(res, self.best_details):
                self.best_fitness = res["fitness"]
                self.best_position = self.population[i].copy()
                self.best_details = res

    def tournament_select(self) -> int:
        """Selects the best individual from a random tournament subset using Deb's rules."""
        indices = self.rng.choice(self.pop_size, size=self.tournament_size, replace=False)
        best_idx = indices[0]
        for idx in indices[1:]:
            if is_better(self.eval_details[idx], self.eval_details[best_idx]):
                best_idx = idx
        return best_idx

    def optimize(self) -> Dict[str, Any]:
        """
        Executes Genetic Algorithm optimization across generations.
        Returns convergence curve, best dispatch schedule, and metrics.
        """
        start_time = time.perf_counter()
        self.initialize_population()
        self.convergence_curve = [self.best_details.get("operating_cost", self.best_fitness)]

        for gen in range(1, self.max_iter + 1):
            new_pop = np.zeros_like(self.population)

            # Sort population indices using Deb's rules
            sorted_indices = sorted(
                range(self.pop_size),
                key=lambda idx: (0 if self.eval_details[idx].get("is_feasible", False) else 1,
                                 self.eval_details[idx].get("operating_cost", self.eval_details[idx]["fitness"]) if self.eval_details[idx].get("is_feasible", False) else self.eval_details[idx]["fitness"])
            )

            # Preserve elites
            for e in range(self.elite_count):
                e_idx = sorted_indices[e]
                new_pop[e] = self.population[e_idx].copy()

            # Offspring generation
            child_idx = self.elite_count
            while child_idx < self.pop_size:
                p1_idx = self.tournament_select()
                p2_idx = self.tournament_select()
                parent1 = self.population[p1_idx]
                parent2 = self.population[p2_idx]

                # Crossover
                if self.rng.random() < self.crossover_rate:
                    alpha = self.rng.random(self.dim)
                    child1 = alpha * parent1 + (1.0 - alpha) * parent2
                    child2 = (1.0 - alpha) * parent1 + alpha * parent2
                else:
                    child1 = parent1.copy()
                    child2 = parent2.copy()

                # Mutation
                for child in (child1, child2):
                    if child_idx < self.pop_size:
                        mutation_mask = self.rng.random(self.dim) < self.mutation_rate
                        sigma = 0.05 * (self.ub - self.lb)
                        child += mutation_mask * self.rng.normal(0, sigma, self.dim)
                        child = np.clip(child, self.lb, self.ub)
                        new_pop[child_idx] = child
                        child_idx += 1

            self.population = new_pop
            for i in range(self.pop_size):
                res = self.objective_evaluator(self.population[i])
                self.fitness[i] = res["fitness"]
                self.eval_details[i] = res

                if is_better(res, self.best_details):
                    self.best_fitness = res["fitness"]
                    self.best_position = self.population[i].copy()
                    self.best_details = res

            best_val = self.best_details.get("operating_cost", self.best_fitness)
            self.convergence_curve.append(best_val)

        self.execution_time = time.perf_counter() - start_time
        logger.info(
            f"GA completed in {self.execution_time:.3f}s. "
            f"Best Cost: ${self.best_details.get('operating_cost', self.best_fitness):.2f}"
        )

        return {
            "algorithm": "GA",
            "best_fitness": self.best_fitness,
            "best_operating_cost": self.best_details.get("operating_cost", self.best_fitness),
            "best_position": self.best_position,
            "best_details": self.best_details,
            "convergence_curve": self.convergence_curve,
            "execution_time": self.execution_time,
            "iterations": self.max_iter,
            "pop_size": self.pop_size
        }
