from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort
import nltk
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.corpus import stopwords

from .auth import login_required
from .db import get_db

bp = Blueprint("dict", __name__)

# Used when tokenizing words
sentence_re = r'''(?x)      # set flag to allow verbose regexps
        (?:[A-Z]\.)+        # abbreviations, e.g. U.S.A.
      | \w+(?:-\w+)*        # words with optional internal hyphens
      | \$?\d+(?:\.\d+)?%?  # currency and percentages, e.g. $12.40, 82%
      | \.\.\.              # ellipsis
      | [][.,;"'?():_`-]    # these are separate tokens; includes ], [
    '''
grammar = r"""
    NP:
        {<DT>?<JJ.*|NN.*>+<NN.*>}
    PP: 
        {<DT>?<JJ.*|NN.*>*<NN.*><IN><DT>?<JJ.*|NN.*>*<NN.*>}
    VP: 
        {<VB.*><RB.*>*<IN|TO>*<RB.*>+}
        {<VB.*><RB.*>*<IN|TO>*<DT>?<NP|NN.*>+}
        {<RB.*>+<VB.*>}
        {<VB.*><RB.*>+}
        {<VB.*>+<RP>*<DT>?<NP|PP|RB.*|NN.*>+}
    """
punctuations = "[].,;\"\'?():_`-"
lemmatizer = WordNetLemmatizer()
stopwords = stopwords.words('english')
chunker = nltk.RegexpParser(grammar)


""" 
Fragment functions 
"""


def nltk_to_wordnet_tag(nltk_tag):
    """ Function to convert nltk tag to wordnet tag. """

    if nltk_tag.startswith('J'):
        return wordnet.ADJ
    elif nltk_tag.startswith('V'):
        return wordnet.VERB
    elif nltk_tag.startswith('N'):
        return wordnet.NOUN
    elif nltk_tag.startswith('R'):
        return wordnet.ADV
    else:
        return None


def normalise(word):
    """ Normalises words to lowercase and lemmatizes it. """

    lowercase_word = word.lower()

    nltk_tagged = nltk.pos_tag([lowercase_word])
    wordnet_tagged = map(lambda x: (x[0], nltk_to_wordnet_tag(x[1])), nltk_tagged)
    lemma = str()
    for word, tag in wordnet_tagged:
        if tag is None:
            lemma = word
        else:
            lemma = lemmatizer.lemmatize(word, tag)
    return lemma


def acceptable_word(word):
    """ Checks conditions for acceptable word: length, stopword. """

    accepted = bool(2 <= len(word) <= 40
                    and word.lower() not in stopwords)
    return accepted


def lemmatize_text(text):
    """ Break the input text down into lemmas. """

    tokens = nltk.regexp_tokenize(text, sentence_re)
    for word in tokens:
        if word in punctuations:
            tokens.remove(word)
    tagged_tokens = nltk.tag.pos_tag(tokens)
    lemmatized_text = [normalise(word) for word, tag in tagged_tokens if acceptable_word(word)]
    return lemmatized_text


def leaves(tree):
    """ Finds phrase leaf nodes of a chunk tree. """

    for subtree in tree.subtrees(filter=lambda t: t.label() != 'S'):
        yield subtree.leaves()


def get_terms(tree):
    """ Get generator with lemmatized phrase words. """

    terms = []
    for leaf in leaves(tree):
        term = [normalise(w) for w, t in leaf if acceptable_word(w)]
        if term:
            terms.append(term)
    return terms


def phrases_from_text(text):
    """ Extract key phrases from text. """

    phrases = []
    tokens = nltk.regexp_tokenize(text, sentence_re)
    tagged_tokens = nltk.tag.pos_tag(tokens)
    tree = chunker.parse(tagged_tokens)
    for leaf in leaves(tree):
        term = [normalise(w) for w, t in leaf if w]
        phrase = ' '.join(term)
        phrases.append(phrase)

    return phrases


def get_word(word_id, check_user=True):
    """ Get a word from the dictionary by id.

        Checks that the id exists and optionally
        that the current user is the author.

        :param word_id: id of word to get
        :param check_user: require the current user to be the author
        :return: the word with author information
        :raise 404: if a word with the given id doesn't exist
        :raise 403: if the current user isn't the author
    """

    word = (
        get_db()
        .execute(
            "SELECT word.id, word.name, word.user_id"
            " FROM word"
            " WHERE word.id = ?",
            (word_id,),
        ).fetchone()
    )

    if word is None:
        abort(404, "Word id {0} doesn't exist.".format(word_id))
    '''
    if check_user and word["user_id"] != g.user["id"]:
        abort(403)
    '''
    return word


def get_phrases(word_id):
    """ Get phrases with the word by the id of the word. """

    phrases = (
        get_db()
        .execute(
            "SELECT DISTINCT phrel.phraseId, phrase.name"
            " FROM phrel"
            " JOIN word ON phrel.wordId = word.id "
            " JOIN phrase ON phrel.phraseId = phrase.id"
            " WHERE phrel.wordId = ? ",
            (word_id,),
        )
        .fetchall()
    )

    if phrases is None:
        abort(404, "Phrases for word id {0} don't exist.".format(word_id))

    return phrases


def get_phrase(word_id, phrase_id):
    """ Get a phrase from the phrase table by the id's of the word and phrase"""

    phrase = (
        get_db()
        .execute(
            "SELECT phrel.phraseId, phrase.name"
            " FROM phrel"
            " JOIN word ON phrel.wordId = word.id "
            " JOIN phrase ON phrel.phraseId = phrase.id"
            " WHERE phrel.wordId = ? AND phrel.phraseId = ? ",
            (word_id, phrase_id),
        )
        .fetchone()
    )

    if phrase is None:
        abort(404, "Phrase id {0} for word doesn't exist.".format(word_id))
    return phrase


def get_all_phrase_words(word_id):
    """ Get the words for phrase formation
        by the id's of the word. """

    phrase_words = (
        get_db()
        .execute(
            "SELECT DISTINCT rel.phraseWordId, phrase_word.name"
            " FROM rel"
            " JOIN word main_word ON rel.mainWordId = main_word.id "
            " JOIN word phrase_word ON rel.phraseWordId = phrase_word.id"
            " WHERE rel.mainWordId = ?",
            (word_id,),
        )
        .fetchall()
    )

    if phrase_words is None:
        abort(404, "Words for phrase formation for word id {0} don't exist.".format(word_id))

    return phrase_words


""" 
View functions 
"""


@bp.route("/")
def index():
    """ View the words in the dictionary in alphabetical order. """

    db = get_db()
    words = db.execute(
        "SELECT word.id, word.name FROM word ORDER BY word.name "
    ).fetchall()
    return render_template("dictionary/dictionary.html", words=words)


@bp.route("/<int:word_id>/")
def view_word(word_id):
    """ View a single word and its phrase words in the dictionary. """

    word = get_word(word_id)
    phrases = get_phrases(word_id)
    phrasewords = get_all_phrase_words(word_id)

    return render_template("dictionary/word.html", word=word, phrases=phrases, phrasewords=phrasewords)


@bp.route("/add_text", methods=("GET", "POST"))
@login_required
def add_from_text():
    """ Extract word lemmas, phrases and phrase words from text
        and add them to the dictionary db.
    """

    if request.method == "POST":
        text = request.form["text"]
        error = None
        if not text:
            error = "Text is required."
        if error is not None:
            flash(error)
        else:
            tokens = nltk.regexp_tokenize(text, sentence_re)
            tagged_tokens = nltk.tag.pos_tag(tokens)
            tree = chunker.parse(tagged_tokens)
            terms = get_terms(tree)

            lemmas = lemmatize_text(text)
            phrases = phrases_from_text(text)

            db = get_db()
            for lemma in lemmas:
                db.execute(
                    "INSERT OR IGNORE INTO word (name, user_id) VALUES (?, ?)",
                    (lemma, g.user["id"]),
                )
                db.commit()

            for phrase in phrases:
                db.execute(
                    "INSERT OR IGNORE INTO phrase(name, user_id) VALUES (?, ?)",
                    (phrase, g.user["id"]),
                )
                db.commit()

            for main_word in lemmas:
                for phrasewords in terms:
                    if main_word in phrasewords:
                        for word in phrasewords:
                            if word != main_word and acceptable_word(word):
                                db.execute(
                                    "INSERT OR IGNORE INTO rel (mainWordId, phraseWordId, user_id)"
                                    " SELECT main_id.main_word_id, phrase_id.phrase_word_id, (?) AS user_id"
                                    " FROM (SELECT word.id AS main_word_id, word.user_id FROM word"
                                    " WHERE word.name = ?) main_id"
                                    " JOIN (SELECT word.id AS phrase_word_id, word.user_id FROM word"
                                    " WHERE word.name = ?) phrase_id"
                                    " ON main_id.user_id = phrase_id.user_id",
                                    (g.user["id"], main_word, word),
                                )
                                db.commit()
                                db.execute(
                                    "INSERT OR IGNORE INTO rel (mainWordId, phraseWordId, user_id)"
                                    " SELECT main_id.main_word_id, phrase_id.phrase_word_id, (?) AS user_id"
                                    " FROM (SELECT word.id AS main_word_id, word.user_id FROM word"
                                    " WHERE word.name = ?) main_id"
                                    " JOIN (SELECT word.id AS phrase_word_id, word.user_id FROM word"
                                    " WHERE word.name = ?) phrase_id"
                                    " ON main_id.user_id = phrase_id.user_id",
                                    (g.user["id"], word, main_word),
                                )
                                db.commit()
                for phrase in phrases:
                    if main_word in phrase:
                        db.execute(
                            "INSERT OR IGNORE INTO phrel (phraseId, wordId, user_id)"
                            " SELECT phrase.id, word.id, (?) AS user_id"
                            " FROM phrase JOIN word"
                            " ON phrase.user_id = word.user_id"
                            " WHERE phrase.name = ?"
                            " AND word.name = ?",
                            (g.user["id"], phrase, main_word),
                        )
                        db.commit()

            return redirect(url_for("dict.index"))

    return render_template("dictionary/add_text.html")


@bp.route("/add_word", methods=("GET", "POST"))
@login_required
def add_word():
    """ Add words manually to the dictionary. """

    if request.method == "POST":
        new_word = request.form["word"]
        error = None
        if not new_word:
            error = "Word is required."
        if error is not None:
            flash(error)
        else:
            lemmas = lemmatize_text(new_word)
            db = get_db()
            for lemma in lemmas:
                db.execute(
                    "INSERT INTO word (name, user_id) VALUES (?, ?)",
                    (lemma, g.user["id"]),
                )
                db.commit()
                return redirect(url_for("dict.index"))
    return render_template("dictionary/add_word.html")


@bp.route("/<int:word_id>/edit", methods=("GET", "POST"))
@login_required
def edit_word(word_id):
    """ Edit a word if the current user is the author. """

    word = get_word(word_id)
    phrases = get_phrases(word_id)
    phrasewords = get_all_phrase_words(word_id)

    if request.method == "POST":
        name = request.form["word"]
        error = None

        if not name:
            error = "Word is required."
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE word SET name = ? WHERE id = ?",
                (name, word_id)
            )
            db.commit()
            return redirect(url_for("dict.index"))

    return render_template("dictionary/edit_word.html", word=word, phrases=phrases, phrasewords=phrasewords)


@bp.route("/<int:word_id>/add_phrase_word", methods=("GET", "POST"))
@login_required
def add_phrase_word(word_id):
    """ Edit a word - add phrase word for this word. """

    word = get_word(word_id)

    if request.method == "POST":
        phrase_word = request.form["phrase_word"]
        error = None
        if not phrase_word:
            error = "Word is required."
        if error is not None:
            flash(error)
        else:
            lemmas = lemmatize_text(phrase_word)
            db = get_db()
            for lemma in lemmas:
                db.execute(
                    "INSERT OR IGNORE INTO word (name, user_id) VALUES (?, ?)",
                    (lemma, g.user["id"]),
                )
                db.commit()

                db.execute(
                    "INSERT OR IGNORE INTO rel (mainWordId, phraseWordId, user_id)"
                    " SELECT (?), word.id, (?)"
                    " FROM word"
                    " WHERE word.name = (?)",
                    (word_id, g.user["id"], lemma),
                )
                db.commit()
                db.execute(
                    "INSERT OR IGNORE INTO rel (mainWordId, phraseWordId, user_id)"
                    " SELECT word.id, (?), (?)"
                    " FROM word"
                    " WHERE word.name = (?)",
                    (word_id, g.user["id"], lemma),
                )
                db.commit()

                return redirect(url_for("dict.index"))

    return render_template("dictionary/add_phrase_word.html", word=word)


@bp.route("/<int:word_id>/delete", methods=("POST",))
@login_required
def delete_word(word_id):
    """ Delete a word from the dictionary.

        Ensures that the word exists and
        that the logged in user is the author.
    """

    get_word(word_id)
    db = get_db()
    db.execute(
        "DELETE FROM word WHERE id = ?",
        (word_id,)
    )
    db.commit()

    db.execute(
        "DELETE FROM rel WHERE mainWordId = ? OR phraseWordId = ?",
        (word_id, word_id)
    )
    db.commit()

    db.execute(
        "DELETE FROM phrel WHERE wordId = ?",
        (word_id,)
    )
    db.commit()
    return redirect(url_for("dict.index"))


@bp.route("/<int:word_id>/delete", methods=("POST",))
@login_required
def delete_phrase(word_id, phrase_id):
    """ Delete a phrase from the dictionary. """

    get_phrase(word_id, phrase_id)
    db = get_db()
    db.execute(
        "DELETE FROM phrase WHERE id = ?",
        (phrase_id,)
    )
    db.commit()

    db.execute(
        "DELETE FROM phrel WHERE phraseId = ?",
        (phrase_id,)
    )
    db.commit()

    return redirect(url_for("dict.index"))


@bp.route("/<int:word_id>/delete", methods=("POST",))
@login_required
def delete_phrase_word(word_id, phrase_word_id):
    """ Delete a phrase from the dictionary. """

    get_word(phrase_word_id)
    db = get_db()
    db.execute(
        "DELETE FROM rel WHERE (mainWordId = ? AND phraseWordId = ?) OR (mainWordId = ? AND phraseWordId = ?)",
        (word_id, phrase_word_id, phrase_word_id, word_id)
    )
    db.commit()

    return redirect(url_for("dict.index"))
