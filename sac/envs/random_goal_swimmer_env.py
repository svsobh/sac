"""Implements a swimmer which is sparsely rewarded for reaching a goal"""

import numpy as np
from rllab.core.serializable import Serializable
from rllab.envs.mujoco.swimmer_env import SwimmerEnv
from rllab.misc.overrides import overrides
from rllab.envs.base import Step
from rllab.envs.mujoco.mujoco_env import MujocoEnv
from rllab.misc import logger, autoargs

REWARD_TYPES = ('dense', 'sparse')

class RandomGoalSwimmerEnv(SwimmerEnv):
    """Implements a swimmer which is sparsely rewarded for reaching a goal"""

    @autoargs.arg('ctrl_cost_coeff', type=float,
                  help='cost coefficient for controls')
    def __init__(self,
                 reward_type='dense',
                 goal_reward=10,
                 goal_reward_weight=1e-3,
                 goal_radius=0.25,
                 ctrl_cost_coeff=0,
                 *args,
                 **kwargs):
        assert reward_type in REWARD_TYPES

        self._reward_type = reward_type
        self.goal_reward = goal_reward
        self.goal_reward_weight = goal_reward_weight
        self.goal_radius = goal_radius
        self.ctrl_cost_coeff = ctrl_cost_coeff
        MujocoEnv.__init__(self, *args, **kwargs)
        Serializable.quick_init(self, locals())

    def reset(self, goal_position=None, *args, **kwargs):
        if goal_position is None:
            goal_position = np.random.uniform(low=-5.0, high=5.0, size=(2,))

        self.goal_position = goal_position

        return super().reset(*args, **kwargs)

    def get_current_obs(self):
        proprioceptive_observation = super().get_current_obs()
        exteroceptive_observation = self.goal_position

        observation = np.concatenate(
            [proprioceptive_observation,
             exteroceptive_observation]
        ).reshape(-1)

        return observation

    @overrides
    def step(self, action):
        self.forward_dynamics(action)
        next_obs = self.get_current_obs()

        xy_position = self.current_com[:2]
        self.goal_distance = np.sqrt(
            np.sum((xy_position - self.goal_position)**2))

        done = self.goal_distance < self.goal_radius

        if self._reward_type == 'dense':
            goal_reward = -self.goal_distance * self.goal_reward_weight
        elif self._reward_type == 'sparse':
            goal_reward = int(done) * self.goal_reward

        # Add control cost
        if self.ctrl_cost_coeff > 0:
            lb, ub = self.action_bounds
            scaling = (ub - lb) * 0.5
            ctrl_cost = 0.5 * self.ctrl_cost_coeff * np.sum(
                np.square(action / scaling))

            reward = goal_reward - ctrl_cost
        else:
            reward = goal_reward

        return Step(next_obs, reward, done)

    @overrides
    def log_diagnostics(self, paths, *args, **kwargs):
        """Log diagnostic information based on past paths

        TODO: figure out what this should log and implement
        """
        super().log_diagnostics(paths, *args, **kwargs)

        logger.record_tabular('FinalDistanceFromGoal', self.goal_distance)
        logger.record_tabular('OriginDistanceFromGoal',
                              np.sqrt(np.sum(self.goal_position**2)))
