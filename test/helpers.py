from opengold.deck import _DECK

class NoCardException(Exception):
    def __init__(self, card, card_ids):
        self.card = card
        Exception.__init__(self, 'Could not deal fake %s, tried %s' % (card, card_ids))

def fake_deal(r, mocked_key, card_name):
    """
    Fake the next spop to return the specified card (by name).  Throws
    an exception if there are no cards of that sort available in the
    collection when spop is hit.

    To queue several of these, you must do them in REVERSE order.  If
    you want 'tube' second and 'fire' first, then:

    fake_deal(r, 'game:deck', 'tube')
    fake_deal(r, 'game:deck', 'fire')
    """
    card_ids = [i for i in range(len(_DECK)) if _DECK[i].name == str(card_name)]
    orig_pop = r.spop

    def mock_pop(called_key):
        if mocked_key == called_key:
            r.spop = orig_pop
            for card_id in card_ids:
                if r.srem(mocked_key, card_id) == 1:
                    return str(card_id)
                raise NoCardException(card_name, card_ids)
        else:
            print "Warning: expecting to spop(%s), instead got spop(%s)" % (mocked_key, called_key)
            return orig_pop(called_key)

    r.spop = mock_pop
