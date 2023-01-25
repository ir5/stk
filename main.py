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
        [normal(power) for _ in range(normal_counts[power])]

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
    n_other_player_cards: list[int]
    n_other_player_dices: list[int]


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


def enumerate_valid_actions(info: VisibleInfo) -> list[Action]:
    return []


class AgentInterface:
    def select_action(self, info: VisibleInfo) -> Action:
        raise NotImplementedError

    def select_recycle_cards(self, info: VisibleInfo) -> list[int]:
        raise NotImplementedError

    def receive_result(
        self, info: VisibleInfo, control_result: ControlResult
    ) -> None:
        raise NotImplementedError


class Game:
    def __init__(self):
        self.agents = [
            HumanAgent(),
            CPURandom(),
            CPURandom(),
            CPURandom(),
        ]

        self.init_game()

    def init_game(self) -> None:

        self.deck = create_deck()
        self.stacks = [Stack(0, [], [], None) for i in range(5)]
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
        while self.deck:
            if not self.player_stats[current_player].alive:
                continue

            new_card = self.deck.pop()
            self.player_stats[current_player].cards.append(new_card)

            agent = self.agents[current_player]
            action = agent.select_action(
                self.create_visible_info(current_player)
            )

            self.execute_action(current_player, action, agent)

    def create_visible_info(self, current_player: int) -> VisibleInfo:
        info = VisibleInfo(
            stacks=self.stacks,
            cards=self.player_stats[current_player].cards,
            n_dices=self.player_stats[current_player].n_dices,
            player_id=current_player,
            n_other_player_cards=[
                len(player.cards)
                for idx, player in enumerate(self.player_stats)
                if idx != current_player
            ],
            n_other_player_dices=[
                player.n_dices
                for idx, player in enumerate(self.player_stats)
                if idx != current_player
            ],
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
            for _ in range(card_0.power):
                if not self.deck:
                    return
                self.player_stats[current_player].cards.append(self.deck.pop())
            agent.select_recycle_cards(
                self.create_visible_info(current_player)
            )
            return
        elif len(card_indices) == 1 and card_0.card_type == CardType.Recover:
            self.player_stats[current_player].remove_cards(card_indices)
            while (
                self.deck and len(self.player_stats[current_player].cards) < 7
            ):
                self.player_stats[current_player].cards.append(self.deck.pop())
            return

        played_cards = [cards[index] for index in card_indices]
        power, dices = compute_power(played_cards, maximum=False)
        assert action.stack_index is not None
        if self.stacks[action.stack_index].total_power >= power:
            success = False
        else:
            self.stacks[action.stack_index] = Stack(
                total_power=power,
                cards=played_cards,
                dices=dices,
                owner_id=current_player,
            )
            success = True

        control_result = ControlResult(dices, power, success)
        agent.receive_result(
            self.create_visible_info(current_player), control_result
        )


def main():
    pass


if __name__ == "__main__":
    main()
