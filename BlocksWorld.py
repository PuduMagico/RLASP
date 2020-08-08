from ClingoBridge import *
import random
from entities import *
import numpy as np
import pickle


class BlocksWorld:
    def __init__(self, path=None):
        self.clingo = ClingoBridge()
        self.blocks = self.get_blocks()
        if path and len(self.blocks) < 10:
            with open(path, 'rb') as f:
                self.allStates = pickle.load(f)
        elif len(self.blocks) < 10:
            self.allStates = self.generate_all_states()

    def get_random_start_state(self):
        if len(self.blocks) < 10:
            rnd = random.randint(0, len(self.allStates) - 1)
            return self.allStates[rnd]
        else:
            return self.generate_random_start_state()

    def generate_all_states(self):
        self.clingo = ClingoBridge()  # reset clingo

        base = ('base', '')
        self.clingo.add_file('initial-states.lp')
        self.clingo.run([base])
        output = self.clingo.output

        num_states = int(len(output) / 2)

        states = np.full(num_states, object)
        for i in range(0, num_states):
            state_atoms = []
            for atom in output[i]:
                if atom.name == 'state':
                    state_atoms.append(atom)
            states[i] = self.parse_state(state_atoms)
        return states

    def generate_random_start_state(self):
        part_states = []
        random.shuffle(self.blocks)
        placed = []
        t = 0

        for block in self.blocks:
            if 1 / (t + 1) >= random.random():
                part_states.append(PartState(f'on({block.arguments[0]},table)'))
            else:
                rand = random.randint(0, len(placed) - 1)
                part_states.append(PartState(f'on({block.arguments[0]},{placed[rand]})'))

            placed.append(block.arguments[0])
            t += 1

        return State(set(part_states))

    def get_blocks(self):
        self.clingo = ClingoBridge()  # reset clingo

        base = ('base', '')
        self.clingo.add_file('initial-states.lp')
        self.clingo.run([base], n=1)
        output = self.clingo.output[0]

        blocks = []
        for atom in output:
            if atom.name == 'block':
                blocks.append(atom)

        return blocks

    def next_step(self, state: State, action: Action, t):
        self.clingo = ClingoBridge()  # reset clingo
        facts = []

        # add dynmaic rules
        facts.append(('base', ''.join([part_state.clingoString() for part_state in state.locations])))
        facts.append(('base', f'#const t = {t}.'))
        if action:
            facts.append(('base', action.clingoString()))

        # add static main program file
        self.clingo.add_file('blocksworld-mdp.lp')
        self.clingo.run(facts)
        output = self.clingo.output

        available_actions = []
        part_states = []
        max_reward = None
        next_reward = None
        best_action = None

        answer_set = output[-1]  # take last, most optimal output
        for atom in answer_set:
            if atom.name == 'executable':
                available_actions.append(self.parse_action(atom))
            elif atom.name == 'state':
                part_states.append(self.parse_part_state(atom))
            elif atom.name == 'bestAction':
                best_action = self.parse_action(atom)
            elif atom.name == 'nextReward':
                next_reward = atom.arguments[0].number
            elif atom.name == 'maxReward':
                max_reward = atom.arguments[0].number
            else:
                print(f'ERROR: unexpected atom "{atom.name}"')

        return State(set(part_states)), available_actions, best_action, next_reward, max_reward

    def parse_part_state(self, atom: clingo.Symbol) -> PartState:
        on_predicate = atom.arguments[0]
        top_block = on_predicate.arguments[0]
        bottom_block = on_predicate.arguments[1]
        return PartState(f'on({top_block},{bottom_block})')

    def parse_action(self, atom: clingo.Symbol) -> Action:
        move_predicate = atom.arguments[0]
        top_block = move_predicate.arguments[0]
        bottom_block = move_predicate.arguments[1]
        return Action(f'move({top_block},{bottom_block})')

    def parse_state(self, atoms: list) -> State:
        part_states = []
        for partState in atoms:
            part_states.append(self.parse_part_state(partState))
        return State(set(part_states))
