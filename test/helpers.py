import subprocess
import redis
import time
import logging
import sys

if sys.version.find('2.7') == 0:
    import unittest
elif sys.version.find('2.6') == 0:
    import unittest2 as unittest
else:
    print "Python %s not tested with opengold.  Use 2.6 or 2.7." % sys.version

#from threading import Thread

try:
    import opengold
except:
    ## if opengold is not installed, look for it manually.
    sys.path.extend(['../', '.'])

from opengold import deck, game

logging.basicConfig()
LOG = logging.getLogger('opengold')

# def logged_popen(*args, **kwargs):
#     """
#     Call this instead of subprocess.Popen to wrap stdout/stdin in
#     a logger.  Returns the same object.
#     """
#     kwargs = dict(kwargs)
#     kwargs['stdout'] = subprocess.PIPE
#     kwargs['stderr'] = subprocess.PIPE
#     s = subprocess.Popen(*args, **kwargs)
#     Thread(target=logger_run, args=(s, LOG, )).start()
#     return s

# def logger_run(subprocess, log):
#     """
#     Print warning to logger for all stdout.
#     """
#     stdout = subprocess.stdout
#     stderr = subprocess.stderr
#     while True:
#         try:
#             log.warn(stdout.next())
#         except StopIteration:
#             pass
#         try:
#             log.error(stderr.next())
#         except StopIteration:
#             pass

#         if not subprocess.poll():
#             time.sleep(.1)
#             continue
#         else:
#             break

#     log.warn('subprocess died')

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
    card_ids = [i for i in range(len(deck._DECK)) if deck._DECK[i].name == str(card_name)]
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


DB_NAME = 'TestServer'
HOST = "http://localhost:6767"

class TestOpengoldServer(unittest.TestCase):
    """
    Subclass this to get a test case that starts and shuts down both
    the Opengold server instance and mongrel. It will work with the
    "TestServer" Redis db, clearing it between tests.
    """

    @classmethod
    def setUpClass(cls):
        """
        Start up opengold & mongrel.
        """
        cls.server = subprocess.Popen('m2sh start -host localhost',
                                      shell=True,
                                      # stdout=subprocess.PIPE,
                                      # stderr=subprocess.PIPE
                                      )
        cls.app = subprocess.Popen('python opengold/server.py %s' % DB_NAME,
                                   shell=True,
                                   # stdout=subprocess.PIPE,
                                   # stderr=subprocess.PIPE
                                   )

        LOG.info("Waiting for server to start")
        time.sleep(2)
        LOG.info("Finished waiting for server to start")

    @classmethod
    def tearDownClass(cls):
        """
        Shut down opengold & mongrel.
        """
        cls.app.terminate()
        cls.app.wait()
        subprocess.Popen('m2sh stop -host localhost', shell=True)

    def setUp(self):
        """
        Clean DB entirely between tests.
        """
        redis.StrictRedis(db=DB_NAME).flushdb()

COUNTRY_NAMES = 'Afghanistan,Albania,Algeria,Andorra,Angola,Antigua & Deps,Argentina,Armenia,Australia,Austria,Azerbaijan,Bahamas,Bahrain,Bangladesh,Barbados,Belarus,Belgium,Belize,Benin,Bhutan,Bolivia,Bosnia Herzegovina,Botswana,Brazil,Brunei,Bulgaria,Burkina,Burundi,Cambodia,Cameroon,Canada,Cape Verde,Central African Rep,Chad,Chile,China,Colombia,Comoros,Congo,Congo {Democratic Rep},Costa Rica,Croatia,Cuba,Cyprus,Czech Republic,Denmark,Djibouti,Dominica,Dominican Republic,East Timor,Ecuador,Egypt,El Salvador,Equatorial Guinea,Eritrea,Estonia,Ethiopia,Fiji,Finland,France,Gabon,Gambia,Georgia,Germany,Ghana,Greece,Grenada,Guatemala,Guinea,Guinea-Bissau,Guyana,Haiti,Honduras,Hungary,Iceland,India,Indonesia,Iran,Iraq,Ireland {Republic},Israel,Italy,Ivory Coast,Jamaica,Japan,Jordan,Kazakhstan,Kenya,Kiribati,Korea North,Korea South,Kosovo,Kuwait,Kyrgyzstan,Laos,Latvia,Lebanon,Lesotho,Liberia,Libya,Liechtenstein,Lithuania,Luxembourg,Macedonia,Madagascar,Malawi,Malaysia,Maldives,Mali,Malta,Marshall Islands,Mauritania,Mauritius,Mexico,Micronesia,Moldova,Monaco,Mongolia,Montenegro,Morocco,Mozambique,Myanmar, {Burma},Namibia,Nauru,Nepal,Netherlands,New Zealand,Nicaragua,Niger,Nigeria,Norway,Oman,Pakistan,Palau,Panama,Papua New Guinea,Paraguay,Peru,Philippines,Poland,Portugal,Qatar,Romania,Russian Federation,Rwanda,St Kitts & Nevis,St Lucia,Saint Vincent & the Grenadines,Samoa,San Marino,Sao Tome & Principe,Saudi Arabia,Senegal,Serbia,Seychelles,Sierra Leone,Singapore,Slovakia,Slovenia,Solomon Islands,Somalia,South Africa,South Sudan,Spain,Sri Lanka,Sudan,Suriname,Swaziland,Sweden,Switzerland,Syria,Taiwan,Tajikistan,Tanzania,Thailand,Togo,Tonga,Trinidad & Tobago,Tunisia,Turkey,Turkmenistan,Tuvalu,Uganda,Ukraine,United Arab Emirates,United Kingdom,United States,Uruguay,Uzbekistan,Vanuatu,Vatican City,Venezuela,Vietnam,Yemen,Zambia,Zimbabwe'.split(',')

PLAYER_NAMES = 'Joy,Priscilla,Daphne,Denise,Skye,Zariah,Kennedi,Rowan,Francesca,Elisa,Jaylynn,Amira,Lizbeth,Kimora,Kenley,Lauryn,Melina,Gloria,Jaelynn,Abbigail,Arielle,Alyson,Camilla,Brynlee,Liberty,Myla,Alissa,Marlee,Claudia,Hanna,Danika,Sandra,Alanna,Hailee,Jaycee,Nancy,Caylee,Miracle,Gracelyn,Annalise,Liana,Yareli,Cindy,Marisol,Eloise,Lorelei,Asia,Bailee,Helena,Kali,Maeve,Jaida,Justice,Aiyana,Kassandra,Anika,Whitney,Laney,Natalee,Kaia,Olive,Marilyn,Aryanna,Farrah,Clarissa,Halle,Ada,Amani,Janessa,Sylvia,Mckinley,Charlee,Aleena,Skyla,Meghan,Madilynn,Bristol,Giana,Rosa,Tori,Gwendolyn,Kaliyah,Lea,Isabela,Shaniya,Dylan,Averie,Aylin,Kristen,Marie,Hallie,Kaylynn,Zoie,Saniyah,Lesly,Madalynn,Kiana,Kaleigh,Yasmin,Wendy,Anabella,Rihanna,Regina,Eve,Rosalie,Elisabeth,Kristina,Sloane,Amya,Kathleen,Lindsay,June,Aspen,Elsa,Nylah,Perla,Casey,Meredith,Raquel,Siena,Samara,Saniya,Anne,Virginia,Raven,Ayanna,Jaylee,Jaylin,Mckayla,Patricia,Mariam,Sherlyn,Lainey,Nathalie,Shiloh,Maia,Aimee,Isis,Linda,Jazlynn,Raelynn,Angelique,Annabel,Maleah,Ryan,Paityn,Elyse,Adelynn,Ansley,Jadyn,Joslyn,Kourtney,Myah,Diamond,Marina,Bryanna,Cara,Tabitha,Haleigh,Selah,Elsie,Jaylene,Leighton,Lailah,Dahlia,Haven,Amara,Arely,Aliya,Jaylah,Briley,Karlee,Sariah,America,Brinley,Taryn,Amiya,Kailee,Milan,Kaitlin,Greta,Mercedes,Phoenix,Lilianna,Sidney,Armando,Rowan,Taylor,Cade,Colt,Felix,Adan,Jayson,Tristen,Julius,Raul,Braydon,Zayden,Julio,Nehemiah,Darius,Ronald,Louis,Trent,Keith,Payton,Enrique,Jax,Randy,Scott,Desmond,Gerardo,Jett,Dustin,Phillip,Beckett,Ali,Romeo,Kellen,Cohen,Pablo,Ismael,Jaime,Brycen,Larry,Kellan,Keaton,Gunner,Braylen,Brayan,Landyn,Walter,Jimmy,Marshall,Beau,Saul,Donald,Esteban,Karson,Reed,Phoenix,Brenden,Tony,Kade,Jamari,Jerry,Mitchell,Colten,Arthur,Brett,Dennis,Rocco,Jalen,Tate,Chris,Quentin,Titus,Casey,Brooks,Izaiah,Mathew,King,Philip,Zackary,Darren,Russell,Gael,Albert,Braeden,Dane,Gustavo,Kolton,Cullen,Jay,Rodrigo,Alberto,Leon,Alec,Damon,Arturo,Waylon,Milo,Davis,Walker,Moises,Kobe,Curtis,Matteo,August,Mauricio,Marvin,Emerson,Maximilian,Reece,Orlando,River,Bryant,Issac,Yahir,Uriel,Hugo,Mohamed,Enzo,Karter,Lance,Porter,Maurice,Leonel,Zachariah,Ricky,Joe,Johan,Nikolas,Dexter,Jonas,Justice,Knox,Lawrence,Salvador,Alfredo,Gideon,Maximiliano,Nickolas,Talon'.split(',')
