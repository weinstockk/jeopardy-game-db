# Name: Keagan Weintock
# File: models/bot.py

import random

class Bot:

    def __init__(self, name, difficulty):

        self.name = name
        self.difficulty = difficulty

        if difficulty == "easy":
            self.buzz_low = 1.2
            self.buzz_high = 2.0
            self.accuracy = 2

        elif difficulty == "medium":
            self.buzz_low = 0.4
            self.buzz_high = 1.5
            self.accuracy = 1

        else: # hard
            self.buzz_low = 0.2
            self.buzz_high = 2.0
            self.accuracy = 0

    def buzz(self):
        return random.uniform(self.buzz_low, self.buzz_high)

    def answer(self, correct_answer, incorrect_answers):
        answers = incorrect_answers[:self.accuracy].copy()
        answers.append(correct_answer)
        return random.choice(answers)

