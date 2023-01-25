import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CardType(Enum):
    Normal = 1
    Combinable = 2
    Recycle = 3
    Recover = 4
    BuffAdd = 5
    BuffDice = 6


@dataclass
class Card:
    card_type: CardType
    power: Optional[int] = None
    combin_id: Optional[int] = None
    dice_count: Optional[int] = None
    dice_multiply: Optional[int] = None

    def to_str(self) -> str:
        if self.card_type == CardType.Normal:
            assert self.power is not None
            return f"[    {self.power:02d}    ]"
        elif self.card_type == CardType.Combinable:
            mark = "~!@#="
            assert self.power is not None
            assert self.combin_id is not None
            return f"[  ({mark[self.combin_id]}) {self.power:02d}  ]"
        elif self.card_type == CardType.Recycle:
            return f"[<Recycle{self.power}>]"
        elif self.card_type == CardType.Recover:
            return "[*Recovrer*]"
        elif self.card_type == CardType.BuffAdd:
            return f"[    +{self.power}    ]"
        elif self.card_type == CardType.BuffDice:
            assert self.dice_count is not None
            assert self.dice_multiply is not None
            s = "D" * self.dice_count
            if self.dice_multiply > 1:
                s = s + f"x{self.dice_multiply}"
            h = (10 - len(s)) // 2
            return "[" + " " * h + s + " " * (10 - len(s) - h) + "]"
        else:
            raise NotImplementedError


@dataclass
class Stack:
    total_power: int
    cards: list[Card]
    dices: list[int]
    owner_id: Optional[int]


@dataclass
class PlayerStat:
    cards: list[Card]
    n_dices: int
    alive: bool

    def remove_cards(self, indices: list[int]):
        self.cards = [
            card for i, card in enumerate(self.cards) if i not in indices
        ]


def create_deck() -> list[Card]:
    def normal(power: int) -> Card:
        return Card(CardType.Normal, power=power)

    def comb(power: int, combin_id) -> Card:
        return Card(CardType.Combinable, power=power, combin_id=combin_id)

    def recycle(power: int) -> Card:
        return Card(CardType.Recycle, power=power)

    def recover() -> Card:
        return Card(CardType.Recover)

    def buff_add(power: int) -> Card:
        return Card(CardType.BuffAdd, power=power)

    def buff_dice(count: int, multiply: int) -> Card:
        return Card(
            CardType.BuffDice, dice_count=count, dice_multiply=multiply
        )

    normal_counts = [0, 2, 2, 2, 2, 2, 2, 8, 7, 6, 5, 4, 4]  # => 46
    comb_counts = [0, 1, 1, 2, 2, 3, 3]  # => 60

    deck: list[Card] = []
    for power in range(1, 13):
        deck += [normal(power) for _ in range(normal_counts[power])]

    for combin_id in range(5):
        for power in range(1, 7):
            deck += [comb(power, combin_id) for _ in range(comb_counts[power])]

    deck += [recycle(1) for _ in range(3)]
    deck += [recycle(2) for _ in range(3)]
    deck += [recover() for _ in range(6)]  # => 12

    deck += [buff_add(2) for _ in range(4)]
    deck += [buff_add(3) for _ in range(4)]
    deck += [buff_add(5) for _ in range(4)]  # => 12

    deck += [buff_dice(1, 1) for _ in range(8)]
    deck += [buff_dice(1, 2) for _ in range(3)]
    deck += [buff_dice(2, 1) for _ in range(3)]
    deck += [buff_dice(3, 1) for _ in range(3)]  # => 20

    return deck


@dataclass
class VisibleInfo:
    stacks: list[Stack]
    cards: list[Card]
    n_dices: int
    player_id: int
    n_other_player_cards: dict[int, int]
    n_other_player_dices: dict[int, int]
    other_player_alives: dict[int, bool]


@dataclass
class Action:
    card_indices: list[int]
    stack_index: Optional[int] = None


@dataclass
class ControlResult:
    dices: list[int]
    total_power: int
    success: bool


def compute_power(
    cards: list[Card], maximum: bool = True
) -> tuple[int, list[int]]:
    power = 0
    dices = []
    for card in cards:
        if card.card_type == CardType.Normal:
            assert card.power is not None
            power += card.power
        elif card.card_type == CardType.Combinable:
            assert card.power is not None
            power += card.power
        elif card.card_type == CardType.BuffAdd:
            assert card.power is not None
            power += card.power
        elif card.card_type == CardType.BuffDice:
            assert card.dice_count is not None
            assert card.dice_multiply is not None
            if maximum:
                power += card.dice_count * card.dice_multiply * 6
            else:
                dices = [random.randint(1, 6) for _ in range(card.dice_count)]
                power += sum(dices) * card.dice_multiply
    return power, dices


def compute_max_power(
    cards: list[Card]
) -> int:
    power, _ = compute_power(cards, maximum=True)
    return power


def enumerate_valid_actions(info: VisibleInfo) -> list[Action]:
    actions = []
    cards = info.cards

    def is_draw(card: Card) -> bool:
        return card.card_type == CardType.Recycle or card.card_type == CardType.Recover

    def is_power(card: Card) -> bool:
        return card.card_type == CardType.Normal or card.card_type == CardType.Combinable

    def is_buff(card: Card) -> bool:
        return card.card_type == CardType.BuffAdd or card.card_type == CardType.BuffDice

    def check_stacks(candidate_cards: list[Card], indices: list[int]) -> None:
        for stack_idx, stack in enumerate(info.stacks):
            if compute_max_power(candidate_cards) > stack.total_power:
                actions.append(Action(indices, stack_idx))

    for i, card in enumerate(cards):
        if is_draw(card):
            actions.append(Action([i]))

        if is_power(card):
            check_stacks([card], [i])

    def check_power_buff(card_power: Card, card_buff: Card, i: int, j: int):
        if card_buff.card_type == CardType.BuffDice:
            assert card_buff.dice_count is not None
            if info.n_dices < card_buff.dice_count:
                return
        check_stacks([card_power, card_buff], [i, j])

    for i, card1 in enumerate(cards):
        for j, card2 in enumerate(cards):
            if i == j:
                break

            if is_power(card1) and is_buff(card2):
                check_power_buff(card1, card2, i, j)
            if is_power(card2) and is_buff(card1):
                check_power_buff(card2, card1, i, j)
            if card1.card_type == CardType.Combinable and card1.card_type == CardType.Combinable\
               and card1.combin_id == card2.combin_id:
                check_stacks([card1, card2], [i, j])

    return actions


class AgentInterface:
    def select_action(self, info: VisibleInfo) -> Action:
        raise NotImplementedError

    def select_recycle_cards(self, info: VisibleInfo, n_discards: int) -> list[int]:
        raise NotImplementedError

    def receive_result(
        self, info: VisibleInfo, control_result: ControlResult
    ) -> None:
        raise NotImplementedError


class CPURandom(AgentInterface):

    def __init__(self):
        pass

    def select_action(self, info: VisibleInfo) -> Action:
        actions = enumerate_valid_actions(info)
        if len(actions) == 0:
            return Action([])
        else:
            return random.sample(actions, 1)[0]

    def select_recycle_cards(self, info: VisibleInfo, n_discards: int) -> list[int]:
        n = len(info.cards)
        return random.sample(list(range(n)), n_discards)

    def receive_result(
        self, info: VisibleInfo, control_result: ControlResult
    ) -> None:
        pass


def render(info: VisibleInfo, turns: int):
    print("=" * 200)
    print(f"Turn {turns}")
    print()
    for player_idx, n_cards in info.n_other_player_cards.items():
        n_dices = info.n_other_player_dices[player_idx]
        alive = info.other_player_alives[player_idx]
        print(f"Player {player_idx}: {'LEFT' if not alive else ''} card {n_cards} / dice {n_dices}")
    print()

    for i, stack in enumerate(info.stacks):
        line = f"Stack {i}: {stack.total_power}   "
        for card in stack.cards:
            line += card.to_str()
        line += " "
        for dice in stack.dices:
            line += f"({dice})"
        print(line)
        print(f"        Player {stack.owner_id}")
    print()
    print()
    line = ""
    for card in info.cards:
        line += card.to_str() + " "
    print(line)
    print("D" * info.n_dices)


class Game:
    def __init__(self):
        self.agents = [
            CPURandom(),
            CPURandom(),
            CPURandom(),
            CPURandom(),
        ]

        self.init_game()

    def init_game(self) -> None:

        self.deck = create_deck()
        self.stacks = [Stack(0, [], [], None) for i in range(6)]
        random.shuffle(self.deck)
        self.player_stats = [
            PlayerStat(
                cards=[self.deck.pop() for _ in range(7)],
                n_dices=3,
                alive=True,
            )
            for _ in range(len(self.agents))
        ]
        self.alives = len(self.agents)

    def run_game_loop(self) -> None:
        current_player = 0
        turns = 0
        while self.deck and self.alives:
            if turns % 5 == 4:
                stack = random.sample(self.stacks, 1)[0]
                # for stack in self.stacks:
                stack.total_power -= 3
                stack.cards.append(Card(CardType.Normal, -3))

            ego = 0
            if not self.player_stats[current_player].alive:
                current_player = (current_player + 1) % len(self.agents)
                continue

            new_card = self.deck.pop()
            self.player_stats[current_player].cards.append(new_card)

            render(self.create_visible_info(ego), turns)

            agent = self.agents[current_player]
            action = agent.select_action(
                self.create_visible_info(current_player)
            )

            self.execute_action(current_player, action, agent)

            turns += 1
            current_player = (current_player + 1) % len(self.agents)

    def create_visible_info(self, current_player: int) -> VisibleInfo:
        info = VisibleInfo(
            stacks=self.stacks,
            cards=self.player_stats[current_player].cards,
            n_dices=self.player_stats[current_player].n_dices,
            player_id=current_player,
            n_other_player_cards={
                idx: len(player.cards)
                for idx, player in enumerate(self.player_stats)
                if idx != current_player
            },
            n_other_player_dices={
                idx: player.n_dices
                for idx, player in enumerate(self.player_stats)
                if idx != current_player
            },
            other_player_alives={
                idx: player.alive
                for idx, player in enumerate(self.player_stats)
                if idx != current_player
            }
        )
        return info

    def execute_action(
        self, current_player: int, action: Action, agent: AgentInterface
    ) -> None:
        card_indices = action.card_indices
        if len(card_indices) == 0:
            self.player_stats[current_player].alive = False
            self.alives -= 1
            return

        cards = self.player_stats[current_player].cards

        card_0 = cards[card_indices[0]]

        if len(card_indices) == 1 and card_0.card_type == CardType.Recycle:
            self.player_stats[current_player].remove_cards(card_indices)
            assert card_0.power is not None
            for _ in range(card_0.power + 1):
                if not self.deck:
                    return
                self.player_stats[current_player].cards.append(self.deck.pop())
            remove_indices = agent.select_recycle_cards(
                self.create_visible_info(current_player), card_0.power
            )
            self.player_stats[current_player].remove_cards(remove_indices)
            return
        elif len(card_indices) == 1 and card_0.card_type == CardType.Recover:
            self.player_stats[current_player].remove_cards(card_indices)
            while (
                self.deck and len(self.player_stats[current_player].cards) < 7
            ):
                self.player_stats[current_player].cards.append(self.deck.pop())
            return

        played_cards = [cards[index] for index in card_indices]
        self.player_stats[current_player].remove_cards(card_indices)

        power, dices = compute_power(played_cards, maximum=False)
        assert action.stack_index is not None
        if self.stacks[action.stack_index].total_power >= power:
            success = False
        else:
            prev_owner = self.stacks[action.stack_index].owner_id
            if prev_owner is not None:
                self.player_stats[prev_owner].n_dices += len(self.stacks[action.stack_index].dices)

            self.stacks[action.stack_index] = Stack(
                total_power=power,
                cards=played_cards,
                dices=dices,
                owner_id=current_player,
            )
            success = True

        control_result = ControlResult(dices, power, success)
        if success:
            self.player_stats[current_player].n_dices -= len(dices)

        agent.receive_result(
            self.create_visible_info(current_player), control_result
        )


def main():
    game = Game()
    game.run_game_loop()


if __name__ == "__main__":
    main()
