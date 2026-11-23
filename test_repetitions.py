from textsentinel.repetitions import (find_frequent_words, find_repeated_bigrams,
                                      find_repeated_words, load_stopwords, tokenize)


def test_tokenize_apostrophe():
    assert [t.word for t in tokenize("м'ясо та пів'яблука")] == ["м'ясо", "та", "пів'яблука"]


def test_repeated_words():
    assert len(find_repeated_words("Це це тест")) == 1
    assert find_repeated_words("Так було. Так буде.") == []
    assert find_repeated_words("Я знаю, що, що б не було") == []


def test_frequent_words():
    issues = find_frequent_words("кіт кіт кіт пес", stopwords=set(), min_length=3)
    assert len(issues) == 1 and issues[0].fragment == "кіт"


def test_repeated_bigrams():
    text = "красивий день. красивий день, красивий день"
    assert len(find_repeated_bigrams(text, min_count=3, stopwords=set())) == 1


def test_stopwords_loaded():
    assert "що" in load_stopwords()
