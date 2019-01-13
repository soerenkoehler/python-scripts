#!/usr/bin/env python3
#pylint: disable=C0111

from copy import deepcopy


class Sudoku:  # pylint:disable=C0103
    def __init__(self, initial_numbers):
        # initialize 9x9 array with sets of allowed numbers
        self.allowed = [[set(range(1, 10))
                         for x in range(0, 9)]
                        for y in range(0, 9)]
        # initialize 9x9 array for solution
        self.final = [[0 for x in range(0, 9)] for y in range(0, 9)]
        # load predefined numbers (a list of 9 strings with 9 characters each)
        for y in range(0, 9):
            for x in range(0, 9):
                n = initial_numbers[y][x:x + 1]
                if n != " ":
                    self.put_number(x, y, int(n))

    # main loop
    def solve(self):
        if not Sudoku._apply_to_first(self._is_undef, self._mutate):
            print(self)

    # find undefined fields
    def _is_undef(self, x, y):
        return self.final[y][x] == 0

    # try allowed numbers for this field on new deepcopies
    def _mutate(self, x, y):
        for n in self.allowed[y][x]:
            mutated = deepcopy(self)
            mutated.put_number(x, y, n)
            mutated.solve()

    def put_number(self, x, y, n):
        # set the field x,y to n
        self.final[y][x] = n
        self.allowed[y][x] = set()
        # collect fields whose allowed number must be updated
        xx = x - x % 3
        yy = y - y % 3
        box = set([(i, j) for i in range(xx, xx + 3)
                   for j in range(yy, yy + 3)])
        row = set([(x, i) for i in range(0, 9)])
        col = set([(i, y) for i in range(0, 9)])
        # update allowed numbers
        for i, j in row | col | box:
            if n in self.allowed[j][i]:
                self.allowed[j][i].remove(n)
        # now set all field where's left only one allowed number
        while Sudoku._apply_to_first(self._is_fixable, self._fix_it):
            pass

    # find undefined fields that can be definitely set
    def _is_fixable(self, x, y):
        return self.final[y][x] == 0 and len(self.allowed[y][x]) == 1

    # set a fixable field
    def _fix_it(self, x, y):
        self.put_number(x, y, self.allowed[y][x].pop())

    # find the first field matching predicate and apply action
    @staticmethod
    def _apply_to_first(predicate, action):
        for x in range(0, 9):
            for y in range(0, 9):
                if predicate(x, y):
                    action(x, y)
                    return True
        return False

    def __str__(self):
        return "\n".join(
            [self._final_line_to_str(l) for l in self.final[0:3]] +
            ["------+-------+------"] +
            [self._final_line_to_str(l) for l in self.final[3:6]] +
            ["------+-------+------"] +
            [self._final_line_to_str(l) for l in self.final[6:9]]
        )

    @staticmethod
    def _final_line_to_str(line):
        return " | ".join([" ".join([str(n) for n in line[i:i + 3]]) for i in range(0, 9, 3)])


def main():
    Sudoku(["   6 9 1 ",
            "16   5 28",
            "7    86 9",
            "84  269 7",
            "  6   2  ",
            "2 579  64",
            "3 84    5",
            "51 9   76",
            " 9 1 3   "]).solve()
    print()
    Sudoku(["    9 8 3",
            "  9    72",
            " 15  24  ",
            "7    1 6 ",
            "  4   5  ",
            " 6 9    4",
            "  12  68 ",
            "82    7  ",
            "9 6 4    "]).solve()


if __name__ == '__main__':
    main()
