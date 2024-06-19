from unittest import TestCase, main

from lark import Lark, Tree


class TestLexer(TestCase):
    def setUp(self):
        pass

    def test_basic(self):
        p = Lark("""
            start: "a" "b" "c" "d"
            %ignore " "
        """)

        res = list(p.lex("abc cba dd"))
        assert res == list('abccbadd')

        res = list(p.lex("abc cba dd", dont_ignore=True))
        assert res == list('abc cba dd')

    def test_subset_lex(self):
        p = Lark("""
            start: "a" "b" "c" "d"
            %ignore " "
        """)

        res = list(p.lex("xxxabc cba ddxx", start_pos=3, end_pos=-2))
        assert res == list('abccbadd')

        res = list(p.lex("aaaabc cba dddd", start_pos=3, end_pos=-2))
        assert res == list('abccbadd')


if __name__ == '__main__':
    main()
