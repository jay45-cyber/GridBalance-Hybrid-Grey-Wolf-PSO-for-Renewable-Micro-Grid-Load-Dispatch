"""
src/ga.py
Standalone Real-Coded Genetic Algorithm (GA) implemented from scratch
for renewable microgrid load dispatch benchmark comparisons.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, List, Callable
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GeneticAlgorithm:
    """
    Real-Coded Genetic Algorithm with Tournament Selection,
    Arithmetic Crossover, Gaussian Mutation, and Elitism.
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

            if self.fitness[i] < self.best_fitness:
                self.best_fitness = self.fitness[i]
                self.best_position = self.population[i].copy()
                self.best_details = res

    def tournament_select(self) -> int:
        """Selects the best individual from a random tournament subset."""
        indices = self.rng.choice(self.pop_size, size=self.tournament_size, replace=False)
        best_idx = indices[0]
        best_fit = self.fitness[best_idx]
        for idx in indices[1:]:
            if self.fitness[idx] < best_fit:
                best_fit = self.fitness[idx]
                best_idx = idx
        return best_idx

    def optimize(self) -> Dict[str, Any]:
        """
        Executes Genetic Algorithm optimization across generations.
        Returns convergence curve, best dispatch schedule, and metrics.
        """
        start_time = time.perf_counter()
        self.initialize_population()
        self.convergence_curve = [self.best_fitness]

        for gen in range(1, self.max_iter + 1):
            new_pop = np.zeros_like(self.population)

            # Preserve elites
            elite_indices = np.argsort(self.fitness)[:self.elite_count]
            for e, e_idx in enumerate(elite_indices):
                new_pop[e] = self.population[e_idx].copy()

            # Generate rest of offspring
            child_idx = self.elite_count
            while child_idx < self.pop_size:
                p1_idx = self.tournament_select()
                p2_idx = self.tournament_select()
                parent1 = self.population[p1_idx]
                parent2 = self.population[p2_idx]

                # Crossover
                if self.rng.random() < self.crossover_rate:
                    # Blend / arithmetic crossover
                    alpha = self.rng.random(self.dim)
                    child1 = alpha * parent1 + (1.0 - alpha) * parent2
                    child2 = (1.0 - alpha) * parent1 + alpha * parent2
                else:
                    child1 = parent1.copy()
                    child2 = parent2.copy()

                # Mutation (Gaussian perturbation)
                for child in (child1, child2):
                    if child_idx < self.pop_size:
                        mutation_mask = self.rng.random(self.dim) < self.mutation_rate
                        sigma = 0.1 * (self.ub - self.lb)
                        child += mutation_mask * self.rng.normal(0, sigma, self.dim)
                        # Boundary clamping
                        child = np.clip(child, self.lb, self.ub)
                        new_pop[child_idx] = child
                        child_idx += 1

            # Update population and evaluate
            self.population = new_pop
            for i in range(self.pop_size):
                res = self.objective_evaluator(self.population[i])
                self.fitness[i] = res["fitness"]
                self.eval_details[i] = res

                if self.fitness[i] < self.best_fitness:
                    self.best_fitness = self.fitness[i]
                    self.best_position = self.population[i].copy()
                    self.best_details = res

            self.convergence_curve.append(self.best_fitness)

        self.execution_time = time.perf_counter() - start_time
        logger.info(
            f"GA completed in {self.execution_time:.3f}s. "
            f"Best Fitness: ${self.best_fitness:.2f}"
        )

        return {
            "algorithm": "GA",
            "best_fitness": self.best_fitness,
            "best_position": self.best_position,
            "best_details": self.best_details,
            "convergence_curve": self.convergence_curve,
            "execution_time": self.execution_time,
            "iterations": self.max_iter,
            "pop_size": self.pop_size
        }
