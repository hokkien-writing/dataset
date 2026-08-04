from __future__ import annotations

import re
import unicodedata

from scripts.wikisource.postprocess import cleanup, fix_orphaned_semicolons
from scripts.processors.base import generate_modified, generate_original

_HEADWORD_RE = re.compile(r"^\*?\s*\*\*(.+?)\*\*\s+(\S+)(?:\s+(\([^)]*\)))?\s*$")
_HYPHEN_SPACE_RE = re.compile(r"(?<=\w)- (?=\w)")

_PUJ_OCR_FIXES: dict[str, str] = {}

_BOOK_PUJ_OCR_FIXES: dict[str, dict[str, str]] = {
    "Dictionary of the Swatow dialect.djvu": {
        "n6ang": "nâng",
        "b2 tôi": "bé tôi",
        "3aⁿ": "ùaⁿ",
        "1âi": "lâi",
        "c5k": "cêk",
        "t6ng": "tn̆g",
        "al5i": "lâi",
        "ka1-thì": "ka-thì",
    },
}


def _clean(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


_BOOK_READING_CORRECTIONS: dict[tuple[str, str, str], str] = {
    ('thâk cṳ; reads aloud, thóiⁿ cṳ', 'reads silently.', '100'): 'thóiⁿ cṳ',
    ('cṳ́ chài; cú cîah; prepare a meal', 'get supper.', '101'): 'cṳ́ chài; cṳ́ cîah',
    ('khó̤ng-cṳ́', 'Confucius.', '101'): 'khóng-cṳ́',
    ('cham-cha, m̄ côi', 'unassorted.', '102'): 'khim-che',
    ('nín sĭ hîaⁿ châ, a hîaⁿ thôaⁿ?', 'Do you use wood or coal as fuel at your house?', '102'): 'nín sĭ hîaⁿ châ, a hîaⁿ thòaⁿ ?',
    ('ôi tit châ khui, bŏi tit kṳ̀ ka-lânh', 'the wedge that rives, is itself nipped fast.', '102'): 'ôi tit châ khui, bŏi tit kṳ̀ ka-lâuh',
    ('cò̤ chài~~~~(;)', 'get the meal ready.', '103'): 'cò̤ chài',
    ('ngō chái', 'the five colors, blue, yellow, carnation, white, and black.', '103'): 'ngŏ chái',
    ('cng cin, châk bīn', 'when the booty is discovered the thief is found.', '105'): 'cng cin, châk hīn',
    ('khak-khak châk-châk ŭ cèng-kŭ', 'there is indisputable proof of it.', '105'): 'khak-khak châk-châk ŭ cèng-kṳ̆',
    ('tī-pó̤ kio sît cú khṳ̀ jīn thóiⁿ sĭ châk cng a m̄ sĭ', 'the person held responsible for the good order of the place, took the owner of the lost articles to see whether those were the stolen goods.', '105'): 'tī-pó̤ kio sit cú khṳ̀ jīn thóiⁿ sĭ châk cng a m̄ sĭ',
    ('châm-chin chùi; treacherous lips, cham-chin chìe', 'treacherous smiles.', '106'): 'châm-chin chìe',
    ('gû tó̤ hwn cháu', 'the cattle are chewing the cud.', '109'): 'gû tó̤ hwn cháu nâng',
    ('chàu', 'Hasty; harsh.', '110'): 'phû-chàu',
    ('i ke lāi m̄ hûa, ē-ē chāu-chāu nău-nău', 'they are not a harmonious family, they have a row every now and then.', '110'): 'i ke lăi m̄ hûa, ē-ē chāu-chāu nău-nău',
    ('bô̤ hîeⁿ àm, ŭ cheⁿ, khó̤-íⁿ hó̤ kîaⁿ lō', 'it is not very dark, the stars are out, and we can go by their light.', '111'): 'bô̤ hìeⁿ àm, ŭ cheⁿ, khó̤-íⁿ hó̤ kîaⁿ lō',
    ('cheⁿ hṳ̂ⁿ', 'uncooked fish.', '111'): 'cheⁿ hṳ̂',
    ('chê tîeh, ío sĭ cîeⁿ-seⁿ', 'have looked it over, and it remains the same.', '111'): 'chê tîeh, ío sĭ cìeⁿ-seⁿ',
    ('chui-chek tŏ̤-lí', 'inscrutable doctrines.', '113'): 'chui-chek tŏ̤-lí ， chek m̄ chut',
    ('cía tê sĭ chèng hue kâi, chèng kaù cn̂g kâi hue bī', 'this tea has had flower petals mixed with it to scent it, till it tastes strongly of the flowers.', '114'): 'cía tê sĭ chèng hue kâi, chèng kàu cn̂g kâi hue bī',
    ('cò̤ chêng cē', 'be kindlier.', '115'): 'èng chêng',
    ('èng chêng; treat kindly, nâng-chêng', 'kindness.', '115'): 'nâng-chêng',
    ('chì-ngīam kùe kâi; that which has already been tested~~~~(.) keng kùe chì-līen', 'has endured trial.', '116'): 'chì-ngīam kùe kâi* - that which has already been tested~~~~(.)\n  - *keng kùe chì-līen',
    ('chī bŏi ṳ̂ah', 'it will not live.', '117'): 'chī bŏi ûah',
    ('taⁿ khéng hûe-thâu pìⁿ hó̤ hŵn bŏ̤i chî', 'if you are now willing to reform, it is not yet too late.', '117'): 'taⁿ khéng hûe-thâu pìⁿ hó̤ hŵn bŏi chî',
    ("chíaⁿ hun; to offer one's pipe, chíaⁿ cíu", 'to offer wine.', '118'): 'chíaⁿ hun',
    ('cŏ̤ chîa', 'to go in a carriage.', '118'): 'cŏ̤ chia',
    ('cīeⁿ jît chiam i pńg to kâi nâng khṳ̀ pó̤ li, pó̤ m̄ chut taⁿ chiam tăi cèng kâi nâng khṳ̀ pó̤, cóng ŏi tit chut', 'some time ago they got the people of his own neighborhood to join in an appeal for his release, but did not thus succeed in setting him at liberty: now they have got the general public to unite in asking for his liberation and he is set free.', '120'): 'cīeⁿ jît chiam i pńg to kâi nâng khṳ̀ pó̤ li, pó̤ m̄ chut：taⁿ chiam tăi cèng kâi nâng khṳ̀ pó̤, cóng ŏi tit chut',
    ('hih-hih chìe', 'to laugh boisterously.', '121'): 'khă-khă chìe',
    ('hih-hih chìe', 'to snicker.', '121'): 'chí-chìe',
    ('pùaⁿ lō côih chíeⁿ; côih lō chieⁿ pak', 'waylay and plunder.', '121'): 'pùaⁿ lō côih chíeⁿ; côih lō chíeⁿ pak',
    ('ngûn-chīeⁿ', 'a silversmith.', '122'): 'ngṳ̂n-chīeⁿ',
    ('i tó̤ bú thih-chieh khṳt nâng thoíⁿ', "he is wielding an iron bludgeon for people's amusement.", '123'): 'i tó̤ bú thih-chieh khṳt nâng thóiⁿ',
    ('nŏ̤ nâng khṳ̀ kio i sie-hŭ chǐm', 'two persons went to help him move it.', '124'): 'nŏ̤ nâng khṳ̀ kio i sie-hŭ chĭm',
    ('cêk koiⁿ thóiⁿ tîeh cò̤ ŏi cēⁿ chío-chío?', 'Why is it that everything appears so quiet?', '126'): 'cêk koiⁿ thóiⁿ tîeh cò̤ ŏi cĕⁿ chío-chío ?',
    ('îong chîn', 'mediocre statesmen.', '126'): 'châi chîn',
    ('cai chiu', 'to put on a false beard.', '127'): 'khoi chiu',
    ('chiu', 'The autumn.', '127'): 'chiu khùi',
    ('chiu hi-hi', 'his beard is very thin.', '127'): 'ĕ pŏ chiu',
    ('chiu khùi; the autumnal season, chiu lîang', 'autumnal coolness.', '127'): 'chiu lîang',
    ('chiu ău; the latter part of autumn, chiu sím', 'the autumnal assizes.', '127'): 'chiu sím',
    ('chiu-siu', 'the late harvest.', '127'): 'chiu ău',
    ('lût chiu', 'to fondle the beard.', '127'): 'so̤ chiu',
    ('âng chiu', 'red bearded.', '127'): 'o chiu',
    ('ĕ pŏ chiu; the beard under the chin, nŏ̤ phuah chiu', 'moustaches.', '127'): 'nŏ̤ phuah chiu',
    ('cho cîah', 'cho khau; coarse food.', '130'): 'cho cîah; cho khau',
    ('phah kàu i bŏ̤i chn̂g bŏi khĭa', 'beat him so he can neither squat nor stand.', '130'): 'phah kàu i bŏi chn̂g bŏi khĭa',
    ('lṳ́ chong-chong àiⁿ khṳ̀ tī kò?', 'What are you going in such haste?', '132'): 'lṳ́ chong-chong àiⁿ khṳ̀ tī kò̤',
    ('cin chó̤ put bú', 'the copy and the original do not agree.', '133'): 'cin chó̤ put hú',
    ('úa sī chù-nâng lṳ́ sĭ nâng-khek', 'I am a native, and you are an alien.', '135'): 'úa sĭ chù-nâng lṳ́ sĭ nâng-khek',
    ('cêk-hûe sni-sĭ chuah tit kùe, ĕ jît cū chuah m̄ kùe', "though you have fooled him once, you won't be able to do it again.", '136'): 'cêk-hûe sui-sĭ chuah tit kùe, ĕ jît cū chuah m̄ kùe',
    ('cêk chùi cĭu thun ô̤h khṳ̀', 'swallowed it all at one mouthful.', '138'): 'cêk chùi cĭu thun lô̤h khṳ̀',
    ('kó-cá tng-sî chut ŭ cêk kâi n̂ang—', 'in ancient times there was a man who—.', '139'): 'kó-cá tng-sî chut ŭ cêk kâi nâng—',
    ('sī íⁿ-keng kè chut kâi cáu-kíaⁿ', 'it is a daughter who is already married.', '139'): 'sĭ íⁿ-keng kè chut kâi cáu-kíaⁿ',
    ('chṳ̀ cîⁿ, chṳ̀ ngûn', 'not first rate money.', '140'): 'chṳ̀ cîⁿ, chṳ̀ ngṳ̂n',
    ('cuí chṳ', 'the larvæ of mosquitoes in water.', '140'): 'cúi chṳ',
    ('hui-chṳ́ phṳ̂e bé-kùa', 'a riding coat of squirrel skin.', '140'): 'hui-chṳ́ phûe bé-kùa',
    ('nío-chṳ́ bṳ́e cīn céng m̄ kiaⁿ sí nâng', "a mouse's tail, even when swelled to the utmost, is nothing to be much frightened at.", '140'): 'nío-chṳ́ búe cĭn céng m̄ kiaⁿ sí nâng',
    ('cía sĭ kìe-cò̤ êk sueh, m̄sĭ tīaⁿ-tîeh cìeⁿ-seⁿ sueh', 'this may be called a whimsical exposition, it is not necessarily thus explained.', '144'): 'cía sĭ kìe-cò̤ êk sueh, msĭ tīaⁿ-tîeh cìeⁿ-seⁿ sueh',
    ('eng-kai; tng-eng-kâi', 'ought; should.', '144'): 'eng-kai; tng-eng-kai',
    ('pńg eng-kâi kâi', "that which it is one's duty to do.", '144'): 'pńg eng-kai kâi',
    ('nâng sim-kuaⁿ, gû saí-tó', 'people have hearts, and cattle have paunches.', '148'): 'nâng sim-kuaⁿ, gû sái-tó',
    ('nŏ̤ nâng sĭm sī siang hâh', 'the two are well suited to each other.', '150'): 'nŏ̤ nâng sĭm sĭ siang hâh',
    ('sim sĭ lī-hāi', 'is very malicious.', '151'): 'sĭm sĭ lī-hāi',
    ('cí khí lok-lok bô̤ ēng, tîeh hiá tōiⁿ-hâk tōiⁿ-hâk kâi cìaⁿ hó̤', 'these are watery and useless, those firm-fleshed and solid ones are the good ones.', '152'): 'cí khí lok-lok bô̤ ēng, tîeh hía tōiⁿ-hâk tōiⁿ-hâk kâi cìaⁿ hó̤',
    ('lṳ́ hāiⁿ-hāiⁿ-kìe sī ûi tîeh sĭm-mih sṳ̄?', 'What are you groaning for?', '152'): 'lṳ́ hāiⁿ-hāiⁿ-kìe sĭ ûi tîeh sĭm-mih sṳ̄',
    ('háng hông kâi muêh', 'an article seldom met with.', '154'): 'háng hông kâi mûeh',
    ('iú hăng', 'a small sum.', '155'): 'íu hăng',
    ('hàu hēng', 'filial conduct.', '156'): 'hàu hĕng',
    ('hău hĕng ŏi kám-tŏng nâng kâi sim', "dutiful behaviour moves people's hearts.", '156'): 'hàu hĕng ŏi kám-tŏng nâng kâi sim',
    ('màiⁿ tak-nn̄g tīo sī-hāu', 'do not waste the time.', '157'): 'màiⁿ tak-nn̄g tīo sî-hāu',
    ('cîah kàu hēng', 'have eaten it till I loathe it.', '160'): 'cîah kàu hĕng',
    ('hîaⁿ mīaⁿ sṳ-îa', 'a counsellor in criminal cases in the local courts.', '164'): 'hîaⁿ mîaⁿ sṳ-îa',
    ('ún-ún kâi sṳ̄ to m̄ cò̤, mńg hàuⁿ lăng-híam', 'he never will do what is safe, but always seeks what is hazardous.', '165'): 'ún-ún kâi sṳ̄ to m̄ cò̤, ḿng hàuⁿ lăng-híam',
    ('cheh hîeh màiⁿ kàuh', 'do not double down the corner of the leaves.', '167'): 'cheh hîeh màiⁿ kauh',
    ('cêk hîeh cêk hiêh àiⁿ khieh bâk', 'double each sheet exactly in the middle to form the edge of the leaf.', '167'): 'cêk hîeh cêk hîeh àiⁿ khieh bâk',
    ('hien kùe hîeh; ĭoⁿ kùe hîeh', 'turn over a leaf.', '167'): 'ĭoⁿ kùe hîeh',
    ('hiên kun', 'a wise monarch.', '168'): 'hîen kun',
    ('huâng-hŏ', 'the empress.', '173'): 'hûang-hŏ',
    ('hō sòi', 'the rain lessens.', '173'): 'hŏ sòi',
    ('hôk ŭ nâng mn̄g lṳ́, lṳ́ tîeh cìeⁿ-seⁿ ìn', 'if anyone should ask you, you must thus answer.', '175'): 'hôk ŭ nâng m̄ng lṳ́, lṳ́ tîeh cìeⁿ-seⁿ ìn',
    ('múaⁿ-tī-kò̤ hâi hong lŵn ngía căi', 'the peaks and ridges all around are very beautiful.', '176'): 'múaⁿ-tī-kò̤ kâi hong lŵn ngía căi',
    ('hō̤ nî~~~~(;)', 'send New Year greetings.', '178'): 'hō̤ nî',
    ('hùhŭe', 'attend a meeting.', '181'): 'hù hŭe',
    ('ang cía sīm sĭ hûa-sŭn', 'husband and wife are in accord.', '183'): 'ang cía sĭm sĭ hûa-sŭn',
    ('cía sṳ̄ sī tī-tîang tó̤ hūaⁿ?', 'Who has the management of this affair?', '184'): 'cía sṳ̄ sĭ tī-tîang tó̤ hūaⁿ',
    ('múa-tī-kò̤ kâi toi-hūaⁿ co̤h kàu khìang-khìang, cúi tōa cìaⁿ bŏ̤i pang', 'the dikes everywhere are strongly made, and when the waters rise will not give way.', '184'): 'múa-tī-kò̤ kâi toi-hūaⁿ co̤h kàu khìang-khìang, cúi tōa cìaⁿ bŏi pang',
    ('hùam bĕ hùam nâng khîa', 'vicious horses find reckless riders.', '185'): 'hùam bé hùam nâng khîa',
    ('cêk kok hûang ki', 'lay up grain against a time of dearth.', '187'): 'cek kok hûang ki',
    ('cí īeⁿ châ ió ûah húe', 'this sort of wood burns well.', '189'): 'cí īeⁿ châ ío ûah húe',
    ('húe cûn; húe hun cûn; húe lūn cûn', 'a steamboat.', '189'): 'húe cûn; húe hun cûn; húe lûn cûn',
    ('húe kŭ', 'the things used about the fire.', '189'): 'húe kṳ̆',
    ('pet hùe têng', 'an honorary tablet to a centenarian.', '191'): 'peh hùe têng',
    ('kîaù hùe', 'salt stores; a good lot of merchandize.', '192'): 'kîam hùe',
    ('i tō̤ thó-ĕ tó̤ húiⁿ khàu', 'he lies on the ground, rolling and crying.', '195'): 'i tŏ̤ thó-ĕ tó̤ húiⁿ khàu',
    ('lṳ́ khip khùi, khip kàu tn̂g-tn̂g, thoíⁿ lṳ́ kâi hùi tī-kò̤ ŏi thìaⁿ a bŏi', 'draw a very long breath, and see whether there is a pain in any part of your lungs.', '195'): 'lṳ́ khip khùi, khip kàu tn̂g-tn̂g, thóiⁿ lṳ́ kâi hùi tī-kò̤ ŏi thìaⁿ a bŏi',
    ('phìⁿ-hun hû', 'a snuff bottle.', '197'): 'phīⁿ-hun hû',
    ('in-cîⁿ hún buah kàu âng-âng', 'made red with rouge.', '198'): 'in-ciⁿ hún buah kàu âng-âng',
    ('hut-jîen cū ŭ nâng lâi', 'suddenly some one came.', '199'): 'hut-jîeh cū ŭ nâng lâi',
    ('pêh hûn pìⁿ cò̤ âng bûn', 'the clouds are turning red.', '199'): 'pêh hûn pìⁿ cò̤ âng hûn',
    ('sìang sīm-mih sin hūn', 'ascertain what rank he has.', '199'): 'sìang sĭm-mih sin hūn',
    ('siet kŭa thông-hwn pò̤-kâi', 'made a canopy of flags.', '201'): 'siet kŭa thông-hwn pò̤-kài',
    ('tit pĕ-bó̤ hâi hwn sim', 'attain the approbation of parents.', '202'): 'tit pĕ-bó̤ kâi hwn sim',
    ('ceh-hwt', 'to punish.', '204'): 'ceh-hŵt',
    ('úa iŭ i bô̤', 'I have some, he has none.', '204'): 'úa ŭ i bô̤',
    ('cē m̄ jû i-kâi ìcū khì', 'if everything is not just as he wishes he gets angry.', '205'): 'cē m̄ jû i-kâi ì cū khì',
    ('sî-hāu bô̤ ĭ, nâng bô̤ ĭ, pēⁿ-cèng īa bô̤ ĭ, ŭ sî ēng îeh hŵu-lío m̄ tâng', 'sometimes when the weather is as usual, the person as usual, and disease the same, the medicine used has not the same effect.', '206'): 'sî-hāu bô̤ ĭ, nâng bô̤ ĭ, pēⁿ-cèng īa bô̤ ĭ, ŭ sî ēng îeh hŵn-lío m̄ tâng',
    ('îeⁿ kim, îeⁿ ngṳ̂n, îeⁿ siak, îeⁿ tâng', 'fuse gold, silver, pewter or brass.', '212'): 'îeⁿ kim, îeⁿ ngṳ̂n, îeⁿ siah, îeⁿ tâng',
    ('húe îeh', 'explosive powders.', '214'): 'jîp îeh',
    ('jîp îeh', 'put in a chemical preparation.', '214'): 'húe îeh',
    ('màiⁿ ĭen-chî', 'go quickly and without delay.', '214'): 'khùe-khùe khṳ̀, màiⁿ ĭen-chî',
    ('îeh-cìⁿ, sĭ cìⁿ-thâu khṳ̀ cṳ́ tâk-îeh kâi', 'poisoned arrows, are those whose points have been steeped in poison.', '214'): 'ieh-cìⁿ, sĭ cìⁿ-thâu khṳ̀ cṳ́ tâk-îeh kâi',
    ('în hái cêk tōa kâi tī-hng', 'all along the coast.', '217'): 'în hái cêk tòa kâi tī-hng',
    ('i kâi cŭe-ak kẁu îong', 'the sum of his iniquities is full.', '220'): 'i kâi cŭe-ak kẁn îong',
    ('îong-īo', 'refulgence.', '220'): 'îong-ĭo',
    ('lṳ́ khṳ̀ kìⁿ kuaⁿ, i ā-sĭ hàm lṳ́ kâi mîaⁿ lṳ́ cū ìn tàⁿ “íuⁿ”', 'when you go before a magistrate, if your name is called you reply “Here”.', '222'): 'lṳ́ khṳ̀ kìⁿ kuaⁿ, i ā-sĭ hàm lṳ́ kâi mîaⁿ lṳ́ cū ìn tàⁿ “íu”',
    ('jêng jît ciàⁿ lâi', 'came another day.', '223'): 'jêng jît cìaⁿ lâi',
    ('jîen', 'Resembling; like.', '226'): 'jîem',
    ('i sûi sĭ ngǒ-lâk-câp hùe mīn-phûe cn̂g kâi bŏi jîo', 'although she is fifty or sixty years old her face is not at all wrinkled.', '228'): 'i sûi sĭ ngŏ-lâk-câp hùe mīn-phûe cn̂g kâi bŏi jîo',
    ('jīo kàu jît-tàu, ā-sǐ jīo m̄ tîeh, lṳ́ cū hó̤ tńg lâi, màiⁿ cài jīo khṳ̀', 'pursue him till noon, and if you do not overtake him, then return, and follow him no farther.', '228'): 'jīo kàu jît-tàu, ā-sĭ jīo m̄ tîeh, lṳ́ cū hó̤ tńg lâi, màiⁿ cài jīo khṳ̀',
    ('sim cē jío tîeh ke-bŭ cū m̄ cěⁿ', "as soon as one's mind is disturbed by domestic matters, he is not tranquil.", '228'): 'sim cē jío tîeh ke-bŭ cū m̄ cĕⁿ',
    ('lṳ̤́ jû-jîak àiⁿ lâi li kio úa tàⁿ', 'if you are coming, then tell me.', '231'): 'lṳ́ jû-jîak âiⁿ lâi li kio úa tàⁿ',
    ('sĭ hṳ̤́ kò̤ kâi mîaⁿ jû', 'it is one of their celebrated scholars.', '231'): 'sĭ hṳ́ kò̤ kâi mîaⁿ jû',
    ('cía cêk ūi sĭ kà-sṳ', 'this is a learned teacher in that religion.', '235'): 'cí cêk ūi sĭ kà-sṳ',
    ('i kà cêk kùe cū pat, chong-men̂g căi', 'if he is once shown how he knows, he is very intelligent.', '235'): 'i kà cêk kùe cū pat, chong-mêng căi',
    ('lṳ́ kaî tōa mîaⁿ úa būe cêng chíaⁿ kà', 'I have not yet asked your name.', '235'): 'lṳ́ kâi tōa mîaⁿ úa būe cêng chíaⁿ kà',
    ('khah jūu, kă m̄tn̆g', 'it is so tough that I cannot bite it in two.', '236'): 'khah ~~jūu~~(jūn), kă m̄ tn̆g',
    ('màiⁿ khṳt i kă tiêh', "don't let him bite you.", '236'): 'màiⁿ khṳt i kă tîeh',
    ('cía ke-húe khût i tú-tú kah ēng', 'this tool is just exactly adapted to his use.', '237'): 'cía ke-húe khṳt i tú-tú kah ēng',
    ('khah-cío kâⁿ châ', 'at right angles, as a magpie carries a stick.', '237'): 'kheh-cío kâⁿ châ',
    ('màiⁿ kah kah miⁿ', 'do not wrap up too closely.', '237'): 'màiⁿ kah khah miⁿ',
    ('phû khí lâi khak tōiⁿ, bŏi phàⁿ', 'they are too heavy, and not at all porous: there is too little yeast in them.', '237'): 'phû khí lâi khak tōiⁿ, bŏi phàⁿ：kàⁿ-bó̤ khah cíe',
    ('soiⁿ lâi kah-tàh thóiⁿ hó̤ mē', 'first try it and see if it fits when inserted.', '237'): 'soiⁿ lâi kah-tàu thóiⁿ hó̤ mē',
    ('cí kâi kah hṳ́ kâi cò̤ cêk-ē khiêh khṳ̀', 'take this and that together in one lot.', '238'): 'cí kâi kah hṳ́ kâi cò̤ cêk-ē khîeh khṳ̀',
    ('i kâi mīaⁿ jû chṳ́', 'his fate is just.', '238'): 'i kâi mīaⁿ kai jû chṳ́',
    ('nâng-nan̂g kâi cai', 'they all know.', '238'): 'nâng-nâng kai cai',
    ('sĭ i kâi ḱn kâi', 'it is what pertains to his functions.', '238'): 'sĭ i kai kẃn kâi',
    ('úa kah i sĭ tan̂g sèⁿ', 'I am of the same surname as he.', '238'): 'úa kah i sĭ tâng sèⁿ',
    ('cêk lîap kâi-cí', 'mustard seed.', '239'): 'cêk lîap kài-cí',
    ('cí koiⁿ chù kâi êⁿ khai sòi', 'the roofbeams of this house are too small.', '239'): 'cí koiⁿ chù kâi êⁿ khah sòi',
    ('i àiⁿ sīm-mih kâi?', 'What does he want?', '239'): 'i àiⁿ sĭm-mih kâi ?',
    ('aǹg kâi jît-thâu hìeⁿ tōa', 'as large as the sun.', '240'): 'àng kâi jît-thâu hìeⁿ tōa',
    ('cía kâi thâu kâi, hṳ́ kâi jī kâi, hṳ́ kâi tŏiⁿ saⁿ kâi', 'this one is the first one, that the second, and the other the third.', '240'): 'cí kâi thâu kâi, hṳ́ kâi jī kâi, hṳ́ kâi tŏiⁿ saⁿ kâi',
    ('u kúi kâi kíaⁿ?', 'How many children have you?', '240'): 'ŭ kúi kâi kíaⁿ ?',
    ('cáu kam hǔam', 'an escaped prisoner.', '241'): 'cáu kam hŭam',
    ('cí hûe kak nâng sǐ tó̤ cîah', 'at this moment every one is eating.', '241'): 'cí hûe kak nâng sĭ tó̤ cîah',
    ('cîah tîeh âu tói ǒi kam; chùi búe ǒi tòa kam', 'it leaves a pleasant taste in the mouth.', '241'): 'cîah tîeh âu tói ŏi kam; chùi búe ŏi tòa kam',
    ('hó̤-hó̤ kâi hǒ kìe-cò̤ kam-lîm', 'a refreshing rain is called a timely rain.', '241'): 'hó̤-hó̤ kâi hŏ kìe-cò̤ kam-lîm',
    ('jû tó̤ cǒ̤ kam, cŏ̤ lô̤', 'like being in a dungeon.', '241'): 'jû tó̤ cŏ̤ kam, cŏ̤ lô̤',
    ('kah chù kak chù kâi ūe ìm', 'each place has its particular dialect.', '241'): 'kak chù kak chù kâi ūe ìm',
    ('kak kok to ǔ nâng kàu cí-kò̤', 'every country has its representatives here.', '241'): 'kak kok to ŭ nâng kàu cí-kò̤',
    ('kak tī-hng īa ǔ', 'every place has it.', '241'): 'kak tī-hng īa ŭ',
    ('ke lǎi kak sṳ̄ sǐ i kẃn', 'all the different sorts of affairs in the household, are under her control.', '241'): 'ke lăi kak sṳ̄ sĭ i kẃn',
    ('khó cǐn, kam lâi', 'when the bitter is exhausted, the sweetness comes.', '241'): 'khó cĭn, kam lâi',
    ('kǔ kam kit', 'a voluntary agreement.', '241'): 'kŭ kam kit',
    ('nâng kak ǔ só̤ chîang', 'each has his own special gift.', '241'): 'nâng kak ŭ só̤ chîang',
    ('soiⁿ khó ǎu kam', 'first the bitter then the sweet.', '241'): 'soiⁿ khó ău kam',
    ('sĭ kam-cek-píaⁿ, a sĭ kam-cek-ko̤, a sǐ kam-cek-thn̂g?', 'Is it worm medicine in lumps, in lozenges, or in powder?', '241'): 'sĭ kam-cek-píaⁿ, a sĭ kam-cek-ko̤, a sĭ kam-cek-thn̂g',
    ('sǐang hó̤ kâi kam-cek-îeh', 'an excellent vermifuge.', '241'): 'sĭang hó̤ kâi kam-cek-îeh',
    ('tàⁿ lâi kak ǔ cêk sueh', 'in speaking each had his own meaning.', '241'): 'tàⁿ lâi kak ŭ cêk sueh',
    ('tŏ̤ kam lǎi ah jîeh kú?', 'How long has he been kept in custody?', '241'): 'tŏ̤ kam lăi ah jîeh kú',
    ('bǒi kang bǒi khó', 'not toilsome.', '242'): 'bŏi kang bŏi khó',
    ('chìn li khṳ̀ kám phǔe', 'if you are cold go and get under the quilt.', '242'): 'chìn li khṳ̀ kám phŭe',
    ('cí cêk ki pit ío ǒi kâm bâk', 'this pen holds the ink better.', '242'): 'cí cêk ki pit ío ŏi kâm bâk',
    ('cí kǐaⁿ muêh thóiⁿ tîeh kâm cúi kâm cúi nē, téng ǔ tǎng', 'this seems to be saturated with water, and weighs heavily.', '242'): 'cí kĭaⁿ mûeh thóiⁿ tîeh kâm cúi kâm cúi nē, téng ŭ tăng',
    ('i sĭ teng pě-kang a sĭ teng bó̤-kang?', 'Is he in mourning for his father or his mother?', '242'): 'i sĭ teng pĕ-kang a sĭ teng bó̤-kang',
    ('i thiaⁿ tîeh kâi sim cū kám-tǒng', 'when he heard it he was much moved.', '242'): 'i thiaⁿ tîeh kâi sim cū kám-tŏng',
    ('khim-thien-kàm sĭ lí thien-bûn kâi sṳ̌', 'the Board of Astronomy regulates astronomical affairs.', '242'): 'khim-thien-kàm sĭ lí thien-bûn kâi sṳ̆',
    ('kiaⁿ kàu phǔe kám miⁿ-miⁿ', 'so afraid that he hid himself under his coverlet.', '242'): 'kiaⁿ kàu phŭe kám miⁿ-miⁿ',
    ('kám tǒ̤ thô̤ tói', 'bury it in the ground.', '242'): 'kám tŏ̤ thô̤ tói',
    ('kám-mǎuⁿ huang hâng', 'affected by the weather.', '242'): 'kám-măuⁿ huang hâng',
    ('kâm pit cňg bâk kâi nâng', 'one who follows literary pursuits.', '242'): 'kâm pit cn̆g bâk kâi nâng',
    ('lǎu-îa kàm tê', 'the god enjoys the tea.', '242'): 'lău-îa kàm tê',
    ('lṳ́ kâi chùi kâm sǐm-mûeh tǒ̤?', 'What have you got in your mouth?', '242'): 'lṳ́ kâi chùi kâm sĭm-mûeh tŏ̤',
    ('lṳ́ kâi phǔe m̄-hó̤ kám thâu kám hîah', 'do not cover your head with your coverlet.', '242'): 'lṳ́ kâi phŭe m̄-hó̤ kám thâu kám hîah',
    ('sǐm sĭ kang-lâng', 'is very wearisome.', '242'): 'sĭm sĭ kang-lâng',
    ('thài-kàm sǐ hûang-tì kâi nôⁿ-pôk', 'the eunuchs are the servants of the Emperor.', '242'): 'thài-kàm sĭ hûang-tì kâi nôⁿ-pôk',
    ('tîeh ǒi kang-lâng khak-khó cìaⁿ ǒi tit hó̤', 'if you can persevere against difficulties all will be well.', '242'): 'tîeh ŏi kang-lâng khak-khó cìaⁿ ŏi tit hó̤',
    ('ǒi kang-khó a bǒi?', 'Is it difficult to do?', '242'): 'ŏi kang-khó a bŏi',
    ('cêng tŏng kang a būe? Is the work begun yet?', 'tiang-sî heng kang? When is the work to begin?', '243'): 'cêng tŏng kang a būe',
    ('i cêng tŏ̤ khî-kang a m̄ cen̂g?', 'Was he there or not?', '243'): 'i cêng tŏ̤ khî-kang a m̄ cêng',
    ('aìⁿ cìeⁿ-seⁿ tàⁿ le hûang-tì kâi kang suaⁿ, mng bw̄n-bw̄n nî ló', 'if it be as you say, then the empire is everlasting.', '244'): 'àiⁿ cìeⁿ-seⁿ tàⁿ le hûang-tì kâi kang suaⁿ, mng bw̄n-bw̄n nî ló',
    ('cí īeⁿ sṳ̄ kâi kang-lîak tōa', 'the efficacy of this is great.', '244'): 'cí īeⁿ sṳ̄ kâi kang-lâk tōa',
    ('cía sĭ lau-kang-ô', 'this is an old traveller; one who knows a ruse.', '244'): 'cía sĭ lău-kang-ô',
    ('kang tîeh cìeⁿ-seⁿ ēng cìaⁿ sĭ en huap', 'expend your strengh thus and that will be according to the right method.', '244'): 'kang tîeh cìeⁿ-seⁿ ēng cìaⁿ sĭen huap',
    ('cí kâi nâng lṳ́ng-kàng', 'this person has fine executive ability.', '245'): 'cí kâi nâng lêng-kàng',
    ('cía sĭ tī cêk káng mâng kâi?', 'From what port is this brought?', '245'): 'cía sĭ tī cêk káng mn̂g kâi',
    ('kap-pô̤ thìo hn̆g sīm kú', 'after a long leap, the toad rests a long time.', '246'): 'kap-pô̤ thìo hn̆g sĭm kú',
    ('tâng cîⁿ kap pńg kāi', 'joint capital.', '246'): 'tâng cîⁿ kap pńg kâi',
    ('cí kâi sîn-seⁿ sĭm kau mîaⁿ', 'this teacher has a great name.', '247'): 'cí kâi sin-seⁿ sĭm kau mîaⁿ',
    ('cía sí kàu-kâi kâi', 'this is a whole one.', '249'): 'cía sĭ kàu-kâi kâi',
    ('khut i thit-thô̤ kàu kàu', 'let him amuse himself as much as he pleases.', '249'): 'khṳt i thit-thô̤ kàu kàu',
    ('nín ke lǎi kâi gûeh câp-kâi-ngṳ̂n kàu nín sṳ-hùi mĕ?', 'Is ten dollars a month sufficient to meet the expenses of your household?', '249'): 'nín ke lăi kâi gûeh câp-kâi-ngṳ̂n kàu nín sṳ-hùi mĕ',
    ('phah kàu phàaⁿ-sìeⁿ', 'beat so much as to maim.', '249'): 'phah kàu phùaⁿ-sìeⁿ',
    ('bûa-a-bûa cū chûntíam-kíaⁿ', 'by successive grindings it is worn away so that there is but little left.', '25'): 'bûa-a-bûa cū chûn tíam-kíaⁿ',
    ('sĭ i kâi a-hiaⁿ a m̄ si?', 'It is his brother is it not?', '25'): 'sĭ i kâi a-hiaⁿ a m̄ sĭ ?',
    ('i său kùe i kâi kău hŭi', 'he has experienced his magnanimity; he has received a liberal donation from him.', '250'): 'i sĭu kùe i kâi kău hŭi',
    ('kauh kàu thăng kîeh cū phùa', 'it has become so tender by long continued dampness that, if you touch it, it tears.', '250'): 'kauh kàu thăng tîeh cū phùa',
    ('khang kâu kâi tó̤d phò kha khṳt cîⁿ', 'one who leads a monkey about is before the shop begging cash.', '250'): 'khang kâu kâi tó̤ phò kha khṳt cîⁿ',
    ('ke kŭi nî cū hó̤ chūa bó̤', 'in a few years more, he may bring home a wife.', '251'): 'ke kúi nî cū hó̤ chūa bó̤',
    ('cí kâi khiah-kha sĭ sûi nîe kè kâi', 'this large footed maid came with her mistress when the latter entered the family.', '252'): 'cí kâi chiah-kha sĭ sûi nîe kè kâi',
    ('i sĭ gê-mn̂g kâi keh tîah, in-ûi gō kong sṳ̄ keh-thò̤ kâi', 'he is a constable who has been dismissed on account of having blundered in public business.', '253'): 'i sĭ gê-mn̂g kâi keh hîah, in-ûi gō kong sṳ̄ keh-thò̤ kâi',
    ('i kh̤t nâng kek tīo lío bŏi tit tńg lâi, tó̤ hṳ́-kò̤ sí khṳ̀', 'being cast off by them, he could not return, and died there.', '254'): 'i khṳt nâng kek tīo lío bŏi tit tńg lâi, tó̤ hṳ́-kò̤ sí khṳ̀',
    ('i mîaⁿ-ko keng-îong', 'he is apt in the calculation of ways and means.', '256'): 'i mîaⁿ-ke keng-îong',
    ('thâu hōⁿ kâi tăng keng jîeh cōi kṳn?', 'How many pounds weight is required to draw the largest of these cross-bows?', '256'): 'thâu hō̤ kâi tăng keng jîeh cōi kṳn ?',
    ('bô̤ lṳ́ cí ki tek-kía̤, cū pâk m̄ cîaⁿ pâi!', 'And you suppose that if we do not have this little bamboo pole of yours we cannot then make up the raft!', '258'): 'bô̤ lṳ́ cí ki tek-kíaⁿ, cū pâk m̄ cîaⁿ pâi !',
    ('cí ki pîaⁿ-bó ŭ jîeh cōi nâng?', 'How many men are there in this detachment of troops?', '258'): 'cí ki piaⁿ-bé ŭ jîeh cōi nâng ?',
    ('i ki ke-hú ngĕ căi, cêk ki hó̤ thâi îaⁿ câp ki', 'his weapons are very hard, so that one of them will outlast ten other ones in a fight.', '258'): 'i ki ke-húe ngĕ căi, cêk ki hó̤ thâi îaⁿ câp ki',
    ('cang ūe ki-chǹg', 'jeered at him.', '259'): 'cang ūe ki-chǹg i',
    ('cèng cîⁿ m̄ siêh, kí cîⁿ bô̤', 'if you are not saving of the common fund, your own share will he missing.', '259'): 'cèng cîⁿ m̄ sieh, kí cîⁿ bô̤',
    ('kí-lôk cêk chṳ̤̀', 'honorably recorded in the Civil Office.', '259'): 'kí-lôk cêk chṳ̀',
    ('sĭ uá ā', 'it is I.', '26'): 'sĭ úa ā',
    ('sĭ ā, tîeh cìeⁿ-seⁿ cìa° tîeh ā', 'yes, that is the way it must be.', '26'): 'sĭ ā , tîeh cìeⁿ-seⁿ cìaⁿ tîeh ā',
    ('uá lâi khṳ̀ ā', 'I am going.', '26'): 'úa lâi khṳ̀ ā',
    ('Stăi-cheng-kok kâi kî-hō̤ sĭ ēng saⁿ-kak n̂g kî, tìn-tang ūe lêng kâi', 'the Chinese flag is a yellow triangular one, with a dragon in the centre.', '260'): 'tăi-cheng-kok kâi kî-hō̤ sĭ ēng saⁿ-kak n̂g kî, tìn-tang ūe lêng kâi',
    ('i âi kî ío tōiⁿ, lṳ́ kâi kî teh i m̄ kùe', 'he is a better player than you, and you cannot win the game against him.', '260'): 'i kâi kî ío tōiⁿ, lṳ́ kâi kî teh i m̄ kùe',
    ('sí kĭaⁿ sṳ̄ kiaⁿ tèng cò̤-nî kì?', 'What is written in the scriptures in regard to this?', '260'): 'cí kĭaⁿ sṳ̄ kiaⁿ tèng cò̤-nî kì ?',
    ('sĭ àⁿ teh chĭeⁿ-kî, a teh ûi-kî?', 'Shall we play chess or draughts?', '260'): 'sĭ àiⁿ teh chĭeⁿ-kî, a teh ûi-kî ?',
    ('cí kǐaⁿ sṳ̄ tó̤ cí kâi tī-hng sĭ tōa pī-kĭ kái', 'in this region the utmost pains is taken to avoid doing this.', '261'): 'cí kĭaⁿ sṳ̄ tó̤ cí kâi tī-hng sĭ tōa pī-kĭ kâi',
    ('cò̤ mih sṳ̄ to bô̤ kĭ-tǎng', 'he acts without respect for anybody.', '261'): 'cò̤ mih sṳ̄ to bô̤ kĭ-tăng',
    ('hŭam sṳ̄ to tiêh kìⁿ kiⁿ', 'for everything there must be a perceptible opening.', '261'): 'hŭam sṳ̄ to tîeh kìⁿ kiⁿ',
    ('kî-jîn sǐ hun cò̤ poih kî', 'the bannermen are divided into eight corps.', '261'): 'kî-jîn sĭ hun cò̤ poih kî',
    ('móng jît móng kuaⁿ khṳ̀ pǐ kìⁿ', 'on a certain day a certain ofiicer was admitted to an audience.', '261'): 'móng jît móng kuaⁿ khṳ̀ pĭ kìⁿ',
    ('úa tâng-cá to hieh-kìⁿ li', 'a little while ago I saw it in turning over the leaves.', '261'): 'úa tâng-cá to hien-kìⁿ li',
    ('ŭ nâng cò̤ cêk kĭaⁿ sṳ̄ cū kĭ cìeⁿ kĭ hìeⁿ, úa li lóng-cóng bô̤ kǐ', 'some people, in doing things, shun this and shun that in superstitious fear: as for me I do not shrink from doing things at any time whatever.', '261'): 'ŭ nâng cò̤ cêk kĭaⁿ sṳ̄ cū kĭ cìeⁿ kĭ hìeⁿ, úa li lóng-cóng bô̤ kĭ',
    ('kia-jîn phûe châi-cṳ́', 'a beautiful lady matched with a talented man.', '262'): 'kia-jîn phùe châi-cṳ́',
    ('tŏ̤ tî kîⁿ, tìeⁿhṳ̂', 'on the margin of the pool, fishing with hook and line.', '262'): 'tŏ̤ tî kîⁿ, tìeⁿ hṳ̂',
    ('i thiaⁿ-tîeh sim sĭ kiaⁿ-hâi', 'when she heard it she was very much startled.', '263'): 'i thiaⁿ-tîeh sĭm sĭ kiaⁿ-hâi',
    ('lú àiⁿ kìa sìn khṳ̀ chù mē? àiⁿ li, úa kò̤ sìn thòa kìa lṳ́', 'Are you going to send a letter home? If so, I will send one along with it.', '263'): 'lṳ́ àiⁿ kìa sìn khṳ̀ chù mē ? àiⁿ li, úa kò̤ sìn thòa kìa lṳ́',
    ('kiaⁿ kàu îang pûah lô̤h', 'so frightened that she fell down in a swoon.', '264'): 'kiaⁿ kàu îang pûah lô̤h khṳ̀',
    ('sang kha kíakíaⁿ ìuⁿ-ìuⁿ', 'very small feet.', '264'): 'sang kha kíaⁿ ìuⁿ-ìuⁿ',
    ('būe ô̤h kîaⁿ soiⁿ ô̤ pue', 'learn to fly before learning to walk.', '265'): 'būe ô̤h kîaⁿ soiⁿ ô̤h pue',
    ('kha thìaⁿ bōi kîaⁿ', 'has a sore foot and cannot walk.', '265'): 'kha thìaⁿ bŏi kîaⁿ',
    ('m̄ cai kíam-tiám khṳ̀', 'did not think to look them over carefully and mark them.', '266'): 'm̄ cai kíam-tíam khṳ̀',
    ('phìa cêk ūi tăi-chîu tó̤ kàm-tok sio-kíam', 'depute a nobleman to oversee the search of the persons of the candidates for admission to the examinations.', '266'): 'phài cêk ūi tăi-chîn tó̤ kàm-tok sio-kíam',
    ('tó̤ hṳ́-kò̤ kiah ŭ kîeh cōi ngṳ̂n?', 'How much money did he get there ?', '266'): 'tó̤ hṳ́-kò̤ kiah ŭ jîeh cōi ngṳ̂n ?',
    ('thâu-mô̤ⁿ kîam căi hàm i ṳ̆-pĭ lâi sói thâu', 'his hair is dirty tell him to get ready to have his head washed.', '267'): 'thâu-mô̤ⁿ kîam căi: hàm i ṳ̆-pĭ lâi sói thâu',
    ('úa cá mêⁿ kîam-kìⁿ io lṳ́ cò̤-pû khṳ̀ thit-thô̤', 'I dreamed last night that I went out for recreation with you.', '267'): 'úa cá mêⁿ kîam-kìⁿ kio lṳ́ cò̤-pû khṳ̀ thit-thô̤',
    ('cúi ah ŏi cíoⁿ keⁿ', 'the wild ducks station a sentinel.', '27'): 'cúi ah ŏi cíeⁿ keⁿ',
    ('áa thiaⁿ-kìⁿ i cong-kú tó̤ ái, ái', 'I hear him grunting all the time.', '27'): 'úa thiaⁿ-kìⁿ i cong-kú tó̤ ái, ái',
    ('i tŏ̤ kîe tèng ngo̤ tîeh úa', 'he met me on the bridge.', '270'): 'i tŏ̤ kîe tèng ngŏ̤ tîeh úa',
    ('kîe-nîe sang pôiⁿ ŭ lâng-kang péⁿ tŏ̤ kŏ̤', 'the sides of the bridge are guarded by a paling.', '270'): 'kîe-nîe sang pôiⁿ ŭ lâng-kang péⁿ tŏ̤ kò̤',
    ('lâm kieⁿs ĭang hiam', 'old ginger is the most pungent.', '270'): 'lâm kieⁿ sĭang hiam',
    ('i bŭn ĭ kìen kâi sṳ̄', 'something rarely seen or heard.', '271'): 'ĭ bŭn ĭ kìen kâi sṳ̄',
    ('kien-kiù', 'steadfast.', '271'): 'kien-kù',
    ('têng tī-kâi sî-hāu ŭ khui kien?', 'At what time was the subscription opened?', '271'): 'tâng tī-kâi sî-hāu ŭ khui kien ?',
    ('kĭen-tì ŭ jîah cōi hôk-sek', 'has bought and laid away ever so many garments.', '272'): 'kĭen-tì ŭ jîeh cōi hôk-sek',
    ('tōa gûeh kĭen; sí gûeh kĭen', 'a long or short month, as fixed by the imperial calendar.', '272'): 'tōa gûeh kĭen, síe gûeh kĭen',
    ('tīam-tīam kìm tŏ̤ pâng lăi', 'kept constantly in the inner appartments, and not allowed to come out.', '273'): 'tīam-tīam kìm tŏ̤ pâng lăi, bô̤ chut lâi',
    ('uî kìm', 'disregard a prohibition.', '273'): 'ûi kìm',
    ('cip kín-kín', 'pick it up carefully with chopsticks.', '274'): 'koih kín-kín',
    ('cí sang ôi bŏi khùaⁿ', 'this pair of shoes is neither too loose nor too tight for me, but they fit exactly.', '274'): 'cí sang ôi bŏi khùaⁿ, bŏi kín, tú-tú kah',
    ('hip kiń-kín', 'closely covered in.', '274'): 'hip kín-kín',
    ('tùe kín tŏ̤ kò̤, tuí m̄ chut', 'it adheres tightly, so that I cannot pull it off.', '274'): 'tùe kín tŏ̤ kò̤, túi m̄ chut',
    ('ciú-ńg m̄ tîeh kío phû cē?', 'Why do you not roll your sleeves higher?', '275'): 'chíu-ńg m̄ tîeh kío phû cē',
    ('cìeⁿ-seⁿ sǹg sĭ kío jîu caŭ cak; that is acting as the exigencies suggest', "being firm or yielding as one's interest demands.", '275'): 'cìeⁿ-seⁿ sǹg sĭ kío jîu cău cak',
    ('hṳ́ kháu khiak-khiak-kìe sĭ tó̤ bōi hió a m̄ sĭ?', 'The sound of a rattle out there is made by some one who is selling dumplings is it not?', '275'): 'hṳ́ kháu khiak-khiak-kìe sĭ tó̤ bōi kío a m̄ sĭ?',
    ('kiong-kiong kèng-kèng; reverently', 'very politely.', '275'): 'kiong-kiong kèng-kèng',
    ('kío ô̤', 'dig oysters from their shells.', '275'): 'kĭo ô̤',
    ('màiⁿ kió-kíang i', 'do not force him to it.', '275'): 'màiⁿ kío-kíang i',
    ('hon̂g hiong hùe kit', 'it happened that the evil omens changed to good ones.', '276'): 'hông hiong hùe kit',
    ('i íⁿ-kang tŏ̤ kuaⁿ mīn côiⁿ kŭ kit', 'he has already certified to it before a magistrate.', '276'): 'i íⁿ-keng tŏ̤ kuaⁿ mīn côiⁿ kŭ kit',
    ('kit cheⁿ cìe lîam', 'a happy star shines upon it.', '276'): 'kit cheⁿ cìe lîm',
    ('lŭn kîp cèng nâng kâi sèⁿ-châng', "discussing people's dispositions.", '276'): 'lŭn kîp cèng nâng kâi sèⁿ-chêng',
    ('sĭ tī-tîang tó̤ kang-kip i cîah?', 'Who supplies him with food?', '276'): 'sĭ tī-tîang tó̤ keng-kip i cîah?',
    ('tîeh khǹg-kòi nín tîeh kîp-cá hûeh thâu', 'must exhort you to at once change your course.', '276'): 'tîeh khǹg-kòi nín tîeh kîp-cá hûe thâu',
    ('úi pí put kîp', 'to compare me with him will not do.', '276'): 'úa pí i put kîp',
    ('bŏ̤i tit kìu', 'cannot save him.', '278'): 'bŏi tit kìu',
    ('thóiⁿ tîhe lêng-ūaⁿ kng', 'it seems brighter.', '279'): 'thóiⁿ tîeh lêng-ūaⁿ kng',
    ('tîeh cū cheⁿ-mêⁿ', 'if you get a spurt from it into your eyes, it will blind you.', '279'): 'mâk khṳt i kiuh tîeh cū cheⁿ-mêⁿ',
    ('cí kaî cîⁿ sĭ pó kǹg kâi', 'this cash is to pay for the string used in stringing the others.', '280'): 'cí kâi cîⁿ sĭ pó kǹg kâi',
    ('cía ki kǹg cúi cū sĭ sĭang ngĕ', 'in this one the steel is of the hardest sort.', '280'): 'cí ki kǹg cúi cū sĭ sĭang ngĕ',
    ('hŭam cìaⁿ peh hwt kâi ko tîeh ka-kī chú kâi lâi cîah cìaⁿ ún-tàng, īa sĭ thèng bói kâi, khíong-ùi ŭ khí ŏi tâk kâi', 'it is safe to eat mushrooms that are of spontaneous growth, if you gather them yourself, but if you carelessly buy them there is danger of their being poisonous and that you may be injured by them.', '280'): 'hŭam cìaⁿ peh hwt kâi ko tîeh ka-kī chú kâi lâi cîah cìaⁿ ún-tàng, īa sĭ thèng bói kâi, khíong-ùi ŭ khí ŏi tâk kâi, cū cîah hāi nâng',
    ('cía kúi kâi phah kó kâi, tī-tîang kâi kó páng ío hó̤', 'of these drummers, which one drums best?', '281'): 'cí kúi kâi phah kó kâi, tī-tîang kâi kó páng ío hó̤',
    ('lăi ko; có ko', "grandfather's sisters.", '281'): 'lău ko, có ko',
    ('cò̤ sṳ̄ kó-kó kùai-kùai', 'does things in a very queer way.', '282'): 'cò̤ sṳ̄ kó-kó kùai-kùai, cò̤ sṳ̄ kú-kú kùai-kùai',
    ('i nâng-khẃn kó-kó nē', 'he is very old fashioned.', '282'): 'i kâi nâng-khẃn kó-kó nē',
    ('kó sî kâi nêng tăi-khài tong-kău', 'old fashioned people are generally honest.', '282'): 'kó sî kâi nâng tăi-khài tong-kău',
    ('kó-ngẃn', 'antiquities.', '282'): 'kó-ńgwn',
    ('pun kó cṳ́ ŭ nâng tōa kó', 'in apportioning the amount which each is to pay, some are assessed more and some less.', '282'): 'pun kó cṳ́ ŭ nâng tōa kó, ŭ nâng sòi kó',
    ('koi bó̤ kok-kok-kiè tó̤ kho koi-kíaⁿ', 'the hen clucks when calling her chickens.', '283'): 'koi bó̤ kok-kok-kìe tó̤ kho koi-kíaⁿ',
    ('kô kàu hua-pa-li-long', 'plaster it on till it is smooth, even and beautiful.', '283'): 'kô kàu hue-pa-li-long',
    ('ŭ lâm li kŏ lâm', 'if you have sons depend on them, if you have no sons then depend on your daughters.', '283'): 'ŭ lâm li kŏ lâm, bô̤ lâm li kŏ ńng',
    ('lâng-ūaⁿ koi-êk cò̤ cìeⁿ-seⁿ', 'change it and make it thus.', '284'): 'lêng-ūaⁿ koi-êk cò̤ cìeⁿ-seⁿ',
    ('mō̤ⁿ thóiⁿ i ŏi kói nē', 'wait and see whether he will amend.', '284'): 'mō̤ⁿ thóiⁿ i ŏi kói mē',
    ('m̄ sĭ cîah cek koi', "it is a hen that won't eat paddy.", '284'): 'm̄ sĭ cîah chek koi',
    ('sieh tîo kòi-mông', 'lay a plot.', '285'): 'siet tîo kòi-mông',
    ('i hṳ́ lăi kâi pâng koiⁿ cōi īa ŭ sói-êk koiⁿ, īa ŭ húe-sît koiⁿ, m̄ pí nâng bô̤ sĭm-mih koiⁿ-keh kâi chù', 'the apartments in it are many: there are bath-rooms and there are cook rooms, and it is not as it is where people have a house with but few rooms.', '286'): 'i hṳ́ lăi kâi pâng koiⁿ cōi：īa ŭ sói-êk koiⁿ, īa ŭ húe-sît koiⁿ, m̄ pí nâng bô̤ sĭm-mih koiⁿ-keh kâi chù',
    ('ēng chôiⁿ-kóiⁿ sâh lío lâi thiu sî', 'boil the cocoon and then wind off the silk.', '286'): 'ēng chôiⁿ-kóiⁿ sâh lío lâi thiu si',
    ('kôih kàu ki siaⁿ sòi-sòi, cū sĭ cṳ-niê siaⁿ', 'modulated his voice to a squeak, like the voice of a woman.', '287'): 'kôih kàu ki siaⁿ sòi-sòi, cū sĭ cṳ-nîe siaⁿ',
    ('cía sĭ kong băng', 'this is a public fund.', '288'): 'cía sĭ kong hăng',
    ('i kâi ăm chun tn̂g-tn̂g tó̤ thó̤iⁿ', 'he was gazing with outstretched neck.', '29'): 'i kâi ăm chun tn̂g-tn̂g tó̤ thóiⁿ',
    ('àm pau cí kâi ì-sṳ̄ tŏ̤ lăi', 'has this meaning involved in it.', '29'): 'àm pau cí kâi ì-sṳ̀ tŏ̤ lăi',
    ('àm-àm khṳ̂ cò̤', 'secretly went and did it.', '29'): 'àm-àm khṳ̀ cò̤',
    ('i kâi ko̤ ciéⁿ côi', 'they work in unison; they pull together.', '290'): 'i kâi ko̤ cíeⁿ côi',
    ('phŏ̤-kò̤ sī tī-tîang?', 'Who is to plead the case?', '290'): 'phŏ̤-kò̤ sĭ tī-tîang ?',
    ('jú kú jú kèng', 'the longer you know him the more you will respect him.', '292'): 'jú kú jú kèng i',
    ('síu bú siang kù', 'the beginning and the end correspond.', '293'): 'síu búe siang kù',
    ('thâk bô̤ kúi kù', 'reads but very few lines a day.', '294'): 'cêk jît thâk bô̤ kúi kù',
    ('bô̤ sin cò̤ ǔ kū?', 'If I have never had new ones how can I have old ones?', '295'): 'bô̤ sin cò̤ ŭ kū',
    ('cĭa kū īeⁿ', 'follow the same old pattern.', '295'): 'cĭu kū īeⁿ',
    ('i sĭ cò̤ cheng kuaⁿ, īn pí sĭ tham kuaⁿ', 'he is a clean handed official, and it is not as if he were a covetous one.', '297'): 'i sĭ cò̤ cheng kuaⁿ, m̄ pí sĭ tham kuaⁿ',
    ('chēng kâi saⁿ tó̤ cṳ̄ kūaⁿ', 'wear a jacket to absorb the perspiration.', '298'): 'chēng kâi saⁿ tó̤ cṳ̀ kūaⁿ',
    ('cṳ̄ kūaⁿ', 'sweating, without exertion.', '298'): 'cṳ̆ kūaⁿ',
    ('kiâm kûaⁿ', 'chills, with but little or no fever.', '298'): 'kîam kûaⁿ',
    ('kuang-mêng cìaⁿ-tai', 'open and above board.', '300'): 'kuang-mêng cìaⁿ-tăi',
    ('khn̂g-kòi i tîeh cai kói kùe', 'exhort him to reform.', '301'): 'khǹg-kòi i tîeh cai kói kùe',
    ('bó̤ íⁿ cṳ̄ kùi', 'the mother is ennobled through her son.', '304'): 'bó̤ íⁿ cṳ́ kùi',
    ('cèng n̂ang lô̤h khṳ̀ kŭi-sàng', 'all made their parting obeisance.', '305'): 'cèng nâng lô̤h khṳ̀ kŭi-sàng',
    ('kun léng ngîam-sok', 'military orders are stringent.', '306'): 'kun lĕng ngîam-sok',
    ('gû-nêk tîeh kuah màiⁿ seⁿ kûn kâi', 'you must get beef which has no tendons in it.', '310'): 'gû-nêk tîeh kuah màiⁿ seⁿ kṳn kâi',
    ('thâu-tèng tà cêk kò̤ o kṳn', 'wore a black head-cloth.', '311'): 'thâu-tèng tà cêk kò̤ o kṳm',
    ('kwn lĭa sĭ lâk nâng, kwn gūa sĭ sì nâng', 'there are six who are mentioned in the contract, and four besides.', '312'): 'kwn lăi sĭ lâk nâng, kwn gūa sĭ sì nâng',
    ('cü kẃn', 'a school-building.', '313'): 'cṳ kẃn',
    ('lĭa gūa kâi chin kẁn lóng-cóng lâi', 'the relatives of the same and of other surnames all came.', '313'): 'lăi gūa kâi chin kẁn lóng-cóng lâi',
    ('kha thâu u', 'the knee.', '315'): 'kha wt',
    ('cía sĭ tek-tek khak-khak kâi cèng-kṳ̄', 'this is substantial proof.', '317'): 'cía sĭ tek-tek khak-khak kâi cèng-kṳ̆',
    ('phah toā khăm, phah lío khŏm-khŏm-kìe', 'sound the great cymbals, and hear their clash.', '319'): 'phah tōa khăm, phah lío khŏm-khŏm-kìe',
    ('tì-kó̤ kâi mn̂g khăm-khăm-kìe?', 'What door is it that is banging?', '319'): 'tī-kó̤ kâi mn̂g khăm-khăm-kìe ?',
    ('khí tōiⁿ, bǒi cù', 'the tooth is sound, it is not decayed at all.', '326'): 'khí tōiⁿ, bŏi cù',
    ('máng bé-khí; to make edging bé-khí pĭⁿ', 'edging.', '326'): 'máng bé-khí',
    ('i kâi khì ngêk-phû hó̤ khṳ̀ chūe sŭn khì, kàng khì kâi îeh lâi cîah', 'this does not agree with him: get some sort of soothing medicine for him to take.', '327'): 'i kâi khì ngêk-phû ； hó̤ khṳ̀ chūe sŭn khì, kàng khì kâi îeh lâi cîah',
    ('i kâi ngŵn khì cok căi', 'his constitution is very strong.', '327'): 'i kâi n̂gwn khì cok căi',
    ('cía cī sĭ khî sṳ̄', 'this is very strange.', '328'): 'cía cū sĭ khî sṳ̄',
    ('koiⁿ-thaû kûiⁿ-khìa kûiⁿ-khìa', 'chuckle-headed.', '329'): 'koiⁿ-thâu kûiⁿ-khìa kûiⁿ-khìa',
    ('i úa tī-tîang cò̤ ău piah suaⁿ?', 'Whom does he rely upon to back him up?', '33'): 'i úa tī-tîang cò̤ ău piah suaⁿ ？',
    ('ău pă, ău âi', 'a step-father or step-mother.', '33'): 'ău pĕ, ău âi',
    ('thoíⁿ tîeh i cū khíong-kŭ', 'when he saw it he was afraid.', '336'): 'thóiⁿ tîeh i cū khíong-kŭ',
    ('khò-thúi khè', 'trowsers that are tied at the ankle.', '338'): 'khò-thúi-khò',
    ('tī-kò̤?', 'Where is is laid away?', '338'): 'khǹg-pàng tī̄-kò̤ ?',
    ('úa thó̤iⁿ lṳ́ kâi jī cêk phien kúi kâi kho', 'I see that one page of your writing has several letters marked as well written.', '338'): 'úa thóiⁿ lṳ́ kâi jī cêk phien kúi kâi kho',
    ('sùe khò̤i', 'the official fee for stamping a document.', '339'): 'sùe khòi',
    ('i seⁿ lâi sĭ a-khòng', 'he is a natural clown.', '341'): 'i seⁿ lâi sĭ a-khòng peh',
    ('khòng', 'Stupid; doltish; simple.', '341'): 'ngà',
    ('tŏng khang-kho̤', 'begin war.', '341'): 'tŏng kang-kho̤',
    ('khu cêk kâi kúi chut lâi teng-tùe', 'forced a demon to come out and attend upon him.', '342'): 'khu cêk kâi kúi chut lâi teng-tùe i',
    ('cí kò̤ lâng-kang lâuh-hâuh, m̄ hóy hàm sin khùa lô̤h khṳ̀', 'this railing is old and shaky, you must not lean your whole weight upon it.', '343'): 'cí kò̤ lâng-kang lâuh-hâuh, m̄ hó̤ hâm sin khùa lô̤h khṳ̀',
    ('cí-kò̤ khah chíen, khíong-ài khùa', 'it is too shallow here, there is danger of running aground.', '343'): 'cí-kò̤ khah chíen, khíong-ùi khùa',
    ('hŵn lâu sin-seⁿ lṳ́ kio úa cài khùʰ cē', 'will trouble you, Sir, to make another effort to divine my fate?', '343'): 'hŵn lâu sin-seⁿ lṳ́ kio úa cài khùaⁿ cē',
    ('khùang-iá', 'a desert; a wilderness.', '345'): 'khùang-ía',
    ('kong cṳ siú cía, cŭe cū khue', 'the leader is held to be guiltiest of all.', '346'): 'kong cṳ síu cía, cŭe cū khue',
    ('tìu-thâi cêk kù thâu-khue cìen-kak ngía căi~~~~(;)', "the brigadier general's helmet and armor are very beautiful.", '346'): 'tìn-thâi cêk kù thâu-khue cìen-kak ngía căi',
    ('úa cēng tòa piaⁿ kio chîo-thêng khue-hôk cōi sîaⁿ-tî', 'I have lead the troops and recovered many cities for the government.', '346'): 'úa cêng tòa piaⁿ kio chîo-thêng khue-hôk cōi sîaⁿ-tî',
    ('cṳ̄ khui thiⁿ-tī kàu taⁿ', 'from the creation till now.', '348'): 'cṳ̆ khui thiⁿ-tī kàu taⁿ',
    ('cĭeⁿ khùi hâⁿ būe cheng-chó̤', 'the first installment is not paid in full.', '349'): 'cĭeⁿ khùi hâiⁿ būe cheng-chó̤',
    ('pháu bé siā cìⁿ', 'shoot arrows from the back of a horse running at full gallop.', '35'): 'pháu bé sīa cìⁿ',
    ('phah bêh', 'sut bêh; to thresh wheat.', '36'): 'phah bêh; sut bêh',
    ('cêk khûn cêk khûn tùi cí-kò̤ kùe', 'they passed by here in companies, making many in all.', '350'): 'cêk khûn cêk khûn tùi cí-kò̤ kùe, cōi căi',
    ('ke khṳ̀n i cū lâi', 'he will come presently.', '350'): 'ke khùn i cū lâi',
    ('khṳ̀n', 'Empty; hungry; famished.', '350'): 'khùn',
    ('bô̤ nâng âiⁿ khṳ̀', 'no one is going.', '351'): 'bô̤ nâng àiⁿ khṳ̀',
    ('i íⁿ-keng khṳ̀ kú kío', 'he went a long time ago.', '351'): 'i íⁿ-keng khṳ̀ kú lío',
    ('cie nàng lâi khui-khṳ́n', 'advertise for laborers in breaking new soil.', '352'): 'cie nâng lâi khui khṳ́n',
    ('pung huang chue khù', 'blown away by the wind.', '352'): 'pun huang chue ~~khù~~(khṳ̀)',
    ('châng īa bw̄n khẃn', 'a vast extent of arable land.', '353'): 'châng tī bw̄n khẃn',
    ('i kâi châng-bn̂g bw̄n khẃn', 'he owns an immeasurable stretch of land.', '353'): 'i kâi châng-hn̂g bw̄n khẃn',
    ('khṳt úa lâi khùi', 'let me go.', '353'): 'khṳt úa lâi khṳ̀',
    ('tīa kîⁿ cêk khwn lóng-cóng àiⁿ kit cò̤ cîeh kâi', 'the enclosure is to be built wholly of stones.', '353'): 'tī kîⁿ cêk khwn lóng-cóng àiⁿ kit cò̤ cîeh kâi',
    ('àiⁿ sàng khṳt tīa-tîang?', 'To whom are you going to give it?', '353'): 'àiⁿ sàng khṳt tī-tîang ?',
    ('bô̤ kò̤ sa-la, thô ĕ mông kò̤ cîeh-pó khṳ̀ kâk i', 'there was nothing else that I could get hold of, and so I caught up a stone from the ground and threw it at him.', '354'): 'bô̤ kò̤ sa-la, thô ĕ mông kò̤ cîeh-pŏ khṳ̀ kâk i',
    ('i kâi lâi sìu hṳ́ tói cò̤-nī tàⁿ?', 'What was said in his letter which has just arrived?', '356'): 'i kâi lâi sìn hṳ́ tói cò̤-nî tàⁿ ?',
    ('lâi châi cò̤ ìn-póiⁿ sĭang hó̤', 'the wood of the pear tree is excellent for making blocks to print upon.', '356'): 'lâi châ cò̤ ìn-póiⁿ sĭang hó̤',
    ('thâu tho̤ sĭ seⁿ lâm a seⁿ nńg?', 'Was her first born a boy or a girl?', '359'): 'thâu tho̤ sĭ seⁿ lâm a seⁿ ńng',
    ('cí hûe kău câp tíam lâng', "it is now past ton o'clock.", '360'): 'cí hûe kàu câp tíam lâng',
    ('tih lâng tíam lóh̤ khṳ̀', 'drop in a few drops.', '360'): 'tih lâng tíam lô̤h khṳ̀',
    ('lâng', 'A term of respect for officers and others; a gentleman.', '361'): 'n̂ng',
    ('làu', 'To purge; to flow off.', '362'): 'sìa',
    ('m̄ hó̤ khah lâu sīn', 'do not take too much anxious thought about it.', '362'): 'm̄ hó̤ khah lâu sîn',
    ('cûn làu kang tang pó lāu chî', 'it is rather late to stop the leak when the boat is in mid channel.', '364'): 'cûn kàu kang tang pó lāu chî',
    ('cĭ kâi lâi chō̤ cúi bŏi lāu', 'this will not leak if water is put in it.', '364'): 'cí kâi lâi chō̤ cúi bŏi lāu',
    ('kung-lĕng ngīam căi', 'the military orders are very strict.', '367'): 'kun-lĕng ngīam căi',
    ('màiⁿ lêng-ngîak', 'do not maltreat him.', '367'): 'màiⁿ lêng-ngîak i',
    ('lí hut, sṳ̄ khîong', 'in a bad cause there is inherent weakness.', '368'): 'lí khut, sṳ̄ khîong',
    ('lí tît, khì câug', 'in a good cause, there is inherent strength.', '368'): 'lí tît, khì càng',
    ('ŭ thiⁿ lí cìaⁿ ŭ lī lí', 'since there is an overruling power there is also an underlying principle in nature.', '368'): 'ŭ thiⁿ lí cìaⁿ ŭ tī lí',
    ('no̤ⁿ-kíaⁿ sòi, lî m̄ khui', 'the children are small and I cannot be away from them.', '370'): 'noⁿ-kíaⁿ sòi, lî m̄ khui',
    ('bô̤ íaⁿ bô̤ ciah kûi sṳ̄ khṳt i tàⁿ kàu ka-ka lîam-lîam', 'things for which there is not a particle of evidence, are made to appear as facts by his well connected statements.', '372'): 'bô̤ íaⁿ bô̤ ciah kâi sṳ̄ khṳt i tàⁿ kàu ka-ka lîam-lîam',
    ('kau-lîam-chieⁿ hó̤ phùa lîen-lŵn-kah-bé', 'a hooked spear is useful in breaking the ranks of armored horses chained together.', '372'): 'kau-lîam-chieⁿ hó̤ phùa lîen-hŵn-kah-bé',
    ('kuaⁿ-liú lîam-mêng', 'magistrates that are incorruptible.', '373'): 'kuaⁿ-hú lîam-mêng',
    ('lāi lîam kuaⁿ', 'deputies appointed by the chancellor to read the essays at an examination.', '373'): 'lăi lîam kuaⁿ',
    ('bô̤ cŭe kâi lîang mīn', 'the freeborn people who are guiltless of crime.', '374'): 'bô̤ cŭe kâi lîang mîn',
    ('bí cêk lîap m̄ kam tak-ūng', 'would not waste a single grain of rice.', '375'): 'bí cêk lîap m̄ kam tak-n̄ng',
    ('cìeⁿ-seⁿ cò̤ sīt-căi i kûi líen-cīeⁿ kùe m̄ khṳ̀', 'indeed, his reputation cannot safely stand that.', '375'): 'cìeⁿ-seⁿ cò̤ sît-căi i kâi líen-cīeⁿ kùe m̄ khṳ̀',
    ('cò̤ kàu sì-piⁿ līang-līang-tît', 'make the four sides perfectly straight and without the least cant either way.', '375'): 'cò̤ kàu sì-piⁿ līang-līang-tît, chŵn bŏi chúa sut-kíaⁿ',
    ('i míh sṳ̄ to sĭ lún-lún lieh-lieh', 'she puts up with all sorts of discomfort.', '375'): 'i mih sṳ̄ to sĭ lún-lún lieh-lieh',
    ('līang', 'Clear, brilliant, transparent, illumined.', '375'): 'lĭang',
    ('chù-piⁿ hù khṳt i lîen-lŭi tîeh', 'his neighbours were implicated by him.', '376'): 'chù-piⁿ hùe khṳt i lîen-lŭi tîeh',
    ('kau-lîen kíu tō̤-kò̤', 'closely interlinked.', '376'): 'kau-lîen kín tŏ̤-kò̤',
    ('kuaⁿ-hú ùiⁿ jŭ kak hieⁿ thŵn-līen', 'the magistrate is going to issue orders for drill in every village.', '376'): 'kuaⁿ-hú àiⁿ jŭ kak hieⁿ thŵn-līen',
    ('úa lîen-tîeh', 'I pity him.', '376'): 'úa lîen-tîeh i',
    ('jît cē phâk têk lîh', 'if exposed to the sun it will crack.', '377'): 'jît cē phâk cū lîh',
    ('lṳ́ thóiⁿ cía jī sĭ lîm sĭm-mîh thiap kâi?', 'What copy do you think has been followed in these letters?', '377'): 'lṳ́ thóiⁿ cía jī sĭ lîm sĭm-mih thiap kâi ?',
    ('khīa tŏ̤ lîm-cíⁿ ĕ', 'standing under the eaves.', '378'): 'khĭa tŏ̤ lîm-cîⁿ ĕ',
    ('tháng tói kâi líang-húng lîo-khí pàng tháng-nîe téng lā', 'take the vermicelli from the bottom of the tub and lay it over the cross-piece, to dry in the air.', '379'): 'tháng tói kâi lîang-hún lîo-khí pàng tháng-nîe téng lā',
    ('tìo cêk tùi tûi-lîn', 'hang up a pair of matched scrolls.', '379'): 'tìo cêk tùi tùi-lîn',
    ('īa cū păi lío', 'that is enough; let be; stay it now.', '379'): 'īa cū pă lío',
    ('ki chú kâi bó', 'ciap ki kâi bó; inferior wife.', '38'): 'ki chú kâi bó ; ciap ki kâi bó',
    ('cîah līo', 'hay and straw for provender.', '380'): 'cháu līo',
    ('cûe-thòaⁿ lô', 'a furnace in which hard coal is burned,', '383'): 'bûe-thòaⁿ lô',
    ('i sĭ tbo̤ chūe sí lō', 'he willfully incurs danger.', '383'): 'i sĭ tŏ̤ chūe sí lō',
    ('cêk tńg lôih', 'a splint hat.', '385'): 'cêk téng lôih',
    ('cṳ̆-âi to sĭ lâu-lâu-lok-lok, bô̤ thang khùaⁿ-ûah', 'has heretofore been constantly drudging, with no opportunity for comfort.', '385'): 'cṳ̆-lâi to sĭ lâu-lâu-lok-lok, bô̤ thang khùaⁿ-ûah',
    ('i si îong-îong lôk-lôk kâi nâng', 'she is a drudge.', '386'): 'i sĭ îong-îong lôk-lôk kâi nâng',
    ('sin tǹg kâi mêh-lôk', 'the blood veesels of the body.', '386'): 'sin tèng kâi mêh-lôk',
    ('suah-lôk kong-chîn kâi sṳ̄, tōa pûaⁿ īa sĭ sì só̤ sái jîen', 'the massacre of the nobles was for the most part made necessary by the circumstances.', '386'): 'suah-lôk kong-chîn kâi sṳ̄, tōa pùaⁿ īa sĭ sì só̤ sái jîen',
    ('cúi mìaⁿ kŏng lô̤', 'do not roil the water.', '388'): 'cúi màiⁿ kŏng lô̤',
    ('sùe cîah lô̤ lâi khîa', 'hire a mule and ride.', '388'): 'sùe ciah lô̤ lâi khîa',
    ('bò̤ ŭn hn̆g', 'not very far.', '39'): 'bô̤ ŭa hn̆g',
    ('bô̤ chên bô̤ lí', 'no correct principles.', '39'): 'bô̤ chêng bô̤ lí',
    ('bô̤ hièⁿ ngía', 'not so handsome.', '39'): 'bô̤ hìeⁿ ngía',
    ('bô̤ khiông', 'inexhaustible.', '39'): 'bô̤ khîong',
    ('ún īa bô̤', 'I also am destitute of them.', '39'): 'úa īa bô̤',
    ('mō̤ⁿ lû', 'a booth beside a grave.', '391'): 'mŏ̤ⁿ lû',
    ('to̤ pèⁿ hṳ́ tńg kâi lŭ àiⁿ ēng thih kâi a sĭ àiⁿ ēng tâng kâi?', 'Do you want the ring which encircles the handle of the knife to be of iron or of brass?', '391'): 'to̤ pèⁿ hṳ́ téng kâi lŭ àiⁿ ēng thih kâi a sĭ àiⁿ ēng tâng kâi ?',
    ('i khut ke-lūi lŭi tîeh', 'she is cumbered with domestic cares.', '393'): 'i khṳt ke-lūi lŭi tîeh',
    ('lūi-cîp cōi, cìaⁿ khṳ̀ càu hûang-sĭang', 'classify and collate all in regular order, and then go and report to the emperor.', '393'): 'lūi-cîp côi, cìaⁿ khṳ̀ càu hûang-sĭang',
    ('i khìa ki lŵn mô̤ⁿ sìⁿ', 'he carried a fan made of the feathers of the argus pheasant.', '395'): 'i khîa ki lŵn mô̤ sìⁿ',
    ('lw̆n sì kâi sî-kāu', 'in time of sedition.', '395'): 'lw̆n sì kâi sî-hāu',
    ('i kong máⁿ', 'grandparents.', '396'): 'a kong máⁿ',
    ('màiⁿ mûeh nap-sap', 'do not soil it.', '396'): 'màiⁿ mûeh nah-sap',
    ('mâiⁿ mîaⁿ mît sèⁿ', 'to conceal one’s name.', '396'): 'mâiⁿ mîaⁿ , mît sèⁿ',
    ('mâk tîeh îu', 'spotted with grease.', '396'): 'mak tîeh îu',
    ('cò̤ sṳ̄ lú-lú máng-máng, êng kâi m̄ ceng-sòi', 'does things in a blundering way, with no circumspection.', '397'): 'cò̤ sṳ̄ lú-lú máng-máng, cn̂g kâi m̄ ceng-sòi',
    ('kîaⁿ māng cē, thāi úa', 'walk rather slowly till I catch up with you.', '398'): 'kîaⁿ māng cē, thăi úa',
    ('lîeng mâng cū khṳ̀', 'hurried off.', '398'): 'lîen mâng cū khṳ̀',
    ('bŏi kîaⁿ méⁿ', 'cannot walk any faster.', '399'): 'bŏi kîaⁿ méⁿ lâi',
    ('i pat khṳ̀ ô̤h mâuⁿ-suaⁿ', 'he has been to learn the incantations of the Tauist priests.', '399'): 'i pat khṳ̀ ô̤h mâuⁿ-suaⁿ huap',
    ('cam-end bō̤', 'a helmet.', '40'): 'cam-eng bō̤',
    ('bú kuaⁿ', 'bú cìang; military officers.', '40'): 'bú kuaⁿ; bú cìang',
    ('khì bûn, cíu bú', 'discard the civil service and enter the military.', '40'): 'khì bûn, cĭu bú',
    ('nīo i mēⁿ', 'let him scold.', '400'): 'nīe i mēⁿ',
    ('mêng-mêng cṳ tang cṳ̌ ŭ cú-cái', 'sheol even has its lord.', '401'): 'mêng-mêng cṳ tang cṳ̆ ŭ cú-cái',
    ('thieng mĕng', "fate; heaven's decree.", '401'): 'thien mĕng',
    ('cin mîaⁿ, sîⁿ jī', 'the true name.', '402'): 'cin mîaⁿ, sît jī',
    ('phah mīⁿ', 'guess riddles.', '402'): 'phah mĭⁿ',
    ('sì mīn, poih hng', 'on every side.', '403'): 'sı̀ mīn, poih hng',
    ('cá mńg nŏ̤ kùe tang lóng-cóng hó̤', 'the early and late crops of the year were both good.', '404'): 'cá ḿng nŏ̤ kùe tang lóng-cóng hó̤',
    ('cí kâi sĭ i kâi mîoⁿ-ī', 'these are his descendants.', '404'): 'cí kâi sĭ i kâi mîoⁿ-ĭ',
    ('kàu-mńg nî cìaⁿ tit cṳ́', 'late in life had a son.', '404'): 'kàu-ḿng nî cìaⁿ tit cṳ́',
    ('lṳ́ hìeⁿ ùaⁿ lâi i mng íⁿ-keng khṳ̀ lío', 'how late you are in coming he has already gone.', '404'): 'lṳ́ hìeⁿ ùaⁿ lâi ：i mng íⁿ-keng khṳ̀ lío',
    ('cĭeⁿ mn̂g', 'approached the door.', '406'): 'cĭeⁿ m̂ng',
    ('hòng tîeh i kâi hīⁿ-kíaⁿ mn̂g', 'boxed him on the ear.', '406'): 'hòng tîeh i kâi hĭⁿ-kíaⁿ mn̂g',
    ('mn̂g khŏng-khŏng-kìe', 'the door is slamming.', '406'): 'm̂ng khŏng-khŏng-kìe',
    ('mn̂g lō', 'openings for trade or work.', '406'): 'm̂ng lō',
    ('mn̂g-pâi', 'door-plate.', '406'): 'm̂ng-pâi',
    ('mó̤', 'A contraction of m̄-hó̤, not good; badly; unsuitable; amis.', '408'): 'mó̤ m̄-hó̤',
    ('bū cúi lío cìaⁿ hó̤ sàṳ tò̤', 'spurt water out of the mouth to settle the dust, and then you may sweep the floor.', '41'): 'bū cúi lío cìaⁿ hó̤ sàu tò̤',
    ('bū sí kuí câp nâng', 'killed several tens of persons by the blast.', '41'): 'bū sí kúi câp nâng',
    ('tâng bû, sâi bû', 'east and west piazzas.', '41'): 'tang bû, sai bû',
    ('bô̤ sĭm-mih mûeh tŏ̤ h̤́u tói', 'there is nothing at all in there.', '411'): 'bô̤ sĭm-mih mûeh tŏ̤ hṳ́ tói',
    ('muêh', 'A thing, matter, or substance; anything between heaven and earth; affairs of life; a creature; a being; persons.', '411'): 'mûeh',
    ('i m̄sĭ nâng', 'he is inhuman.', '413'): 'i msĭ nâng',
    ('né-taⁿ', 'solitary.', '414'): 'né-tăⁿ',
    ('sueh kaù mêng-pêh mêng-pêh nē, khṳt i thiaⁿ', 'explain it very fully now, and let him hear you.', '414'): 'sueh kàu mêng-pêh mêng-pêh nē, khṳt i thiaⁿ',
    ('ún-nêk', 'secreted.', '415'): 'ṳ́n-nêk',
    ('īeⁿ-nêk', 'mutton.', '415'): 'îeⁿ-nêk',
    ('ngà', 'Stupid; silly; foolish.', '416'): 'khòng',
    ('khá ngûn', 'smooth talk.', '417'): 'khá ngân',
    ('chíu buah m̄ khui, khîa ki to̤ lûi kĭo', 'if you cannot wipe it off with you hand, get a knife and scrape it off.', '42'): 'chíu buah m̄ khui, khîa ki to̤ lâi kĭo',
    ('ngíang-kwn thien-bûn', 'to study astrology, and geomancy.', '421'): 'ngíang-kwn thien-bûn hú-chak tī-lí',
    ('hàu-sŭn hŵn seⁿ hàu-sŭn kíaⁿ, ngó-ngêk hŵn seⁿ ngŏ-ngêk jî', 'the filial have filial children, the froward have froward sons.', '422'): 'hàu-sŭn hŵn seⁿ hàu-sŭn kíaⁿ, ngó-ngêk hŵn seⁿ ngó-ngêk jî',
    ('ngŏ hún', 'arrowroot.', '422'): 'ngó hún',
    ('ngut-kim íⁿ-keng ku-ā kâi gûeh', 'up to now it is already several months.', '424'): 'ngṳt-kim íⁿ-keng ku-ā kâi gûeh',
    ('ngŵn pńg si jîeh cōi?', 'What capital had he to start with?', '424'): 'ngŵn pńg sĭ jîeh cōi ?',
    ('ngŵn-kū sĭ cía ĭeⁿ', 'in the beginning it was like this.', '424'): 'n̂gwn-kū sĭ cía ĭeⁿ',
    ('ngṳt-kim íⁿ-keng nǒ̤ nî', 'up to this time, two years have elapsed.', '424'): 'ngṳt-kim íⁿ-keng nŏ̤ nî',
    ('sît-căi si ngŵn mîu', 'are really a set of dunderheads.', '424'): 'sît-căi sĭ ngŵn mîn',
    ('kuè nî', 'to pass from one year to the next; the last day of the year.', '425'): 'kùe nî',
    ('sì nî, nî bō̤, saⁿ nî, tn̂g nî', 'four years in dates makes three full years in time.', '425'): 'sì nî, nî hō̤, saⁿ nî, tn̂g nî',
    ('hàm i sía tieⁿ nía-cēng lâi nía', 'tell him to write a certificate of loan, and come and take a commission.', '427'): 'hàm i sía tieⁿ nía-cèng lâi nía',
    ('mĕng i nía piaⁿ khùⁿ síu ìo-kháu', 'order him to take troops and go and guard an important pass.', '427'): 'mĕng i nía piaⁿ khṳ̀ síu ìo-kháu',
    ('tŏ̤ kiaⁿ, nía bûn-pêng aŭ, cū khí-sin khṳ̀ hṳ̀ jīm', 'after receiving appointment at the capital, he starts on his way to his post.', '427'): 'tŏ̤ kiaⁿ, nía bûn-pêng ău, cū khí-sin khṳ̀ hṳ̀ jīm',
    ('tŏ̤ kuaⁿ-hú kò̤ nía ngûn khṳ̀ chái-bói', 'received money from the magistrate that he might go and buy in some.', '427'): 'tŏ̤ kuaⁿ-hú kò̤ nía ngṳ̂n khṳ̀ chái-bói',
    ('cíe tê sek ngṳ̂n cêk níe', 'this tea is a dime an ounce.', '428'): 'cía tê sek ngṳ̂n cêk níe',
    ('cīⁿ-nîe', 'stipend.', '429'): 'cîⁿ-nîe',
    ('nîe tiêh khah tn̂g', 'find by measuring that it is too long.', '429'): 'nîe tîeh khah tn̂g',
    ('jîem àm cū huang bûe?', 'How late do you rake up the fire?', '43'): 'jîeh àm cū huang bûe ?',
    ('pàng tō̤ mîn-chn̂g kha búe', 'put it there at the foot of the bed.', '43'): 'pàng tŏ̤ mîn-chn̂g kha búe',
    ('níuⁿ i khṳ̀ phṳ̀a', 'collar him and take him to the yamun.', '430'): 'níuⁿ i khṳ̀ phùa',
    ('i keng tèng kâi láu-îa sĭ ngē sin kâi a sĭ ńng sin kâi?', 'Is the idol in that temple, a solid one with painted clothes, or a jointed one with real clothes?', '431'): 'i keng tèng kâi láu-îa sĭ ngĕ sin kâi a sĭ ńng sin kâi ?',
    ('líang pôiⁿ kŭ m̄ khéng tâk ńng', 'neither party was willing to yield at all.', '431'): 'líang pôiⁿ kŭ m̄ khéng tâh ńng',
    ('nō̤ⁿ suaⁿ sie thâh, chíaⁿ chut', 'one mountain on top of another (makes the letter which stands for “exit”), please take your departure.', '433'): 'nŏ̤ⁿ suaⁿ sie thâh, chíaⁿ chut',
    ('oi kŭn i sin-piⁿ', 'snuggles up to her.', '434'): 'oi kṳ̆n i sin-piⁿ',
    ('ói nâng thóiⁿ sṳ̄', 'a dwarf beholding a play.', '434'): 'ói nâng thóiⁿ hì',
    ('ôi khîeh khṳ̀ póiⁿ ôiⁿ-phîaⁿ khṳt i phâk', 'take the shoes and turn their sides to the sun, and let them sun.', '434'): 'ôi khîeh khṳ̀ póiⁿ ôi-phîaⁿ khṳt i phâk',
    ('cí ciah káu ŏi̤ kă nâng a bŏi?', 'Is this dog apt to bite people?', '435'): 'cí ciah káu ŏ̤i kă nâng a bŏi?',
    ('koi-thîo mòng-êk kâi nâng, ciu jīt o̤ mûeh, o̤ kàu chìu sng', 'pedlars who carry their goods on their shoulders, hawk their goods all day, and bawl till their throats ache.', '436'): 'koi-thîo mòng-êk kâi nâng, ciu jît o̤ mûeh, o̤ kàu chùi sng',
    ('àiⁿ pá cí kĭaⁿ sṳ̄ cò̤-nî lâi chù-lì?', 'How shall we arrange this business?', '438'): 'àiⁿ pá cí kĭaⁿ sṳ̄ cò̤-nî lâi chù-tì ?',
    ('cang pâ lâi tói', 'ward off with a shield.', '439'): 'cang pâi lâi tói',
    ('i cò̤ sṳ̄ m̄ káⁿ pāi tîeh mn̂g-huang', 'his conduct shows care not to disgrace the family name.', '439'): 'i cò̤ sṳ̄ m̄ káⁿ pāi tîeh m̂ng-huang',
    ('i tó̤ phah kui-pâi', 'he is playing dominoes.', '439'): 'i tó̤ phah kut-pâi',
    ('bûn kháu', 'the examinations, civil and military.', '44'): 'bûn kháu, bú kháu',
    ('kìa bûn-cṳ', 'î bûn; send dispatches.', '44'): 'kìa bûn-cṳ ； î bûn',
    ('khṳt náng kâi kun cē chong, hía châk-cheⁿ pang', 'as soon as our troops rushed forward, the rebels gave way.', '440'): 'khṳt nâng kâi kun cē chong, hía châk cheⁿ pang',
    ('soiⁿ tì kèng-pang kâi sî-hāu, cò̤-nî hun-hù?', 'What were the orders given by the former emperor at the time of his death?', '440'): 'soiⁿ tì kè-pang kâi sî-hāu, cò̤-nî hun-hù ?',
    ('pàng hui', 'left open.', '442'): 'pàng khui',
    ('sĭ pàng îeⁿ tìeⁿ, and sĭ pàng suaⁿ tìeⁿ?', 'Is it loaned on the security of something afloat or of something ashore?', '442'): 'sĭ pàng îeⁿ tìeⁿ, a sĭ pàng suaⁿ tìeⁿ？',
    ('tâng pâng', 'to room together.', '443'): 'tâng pâng; khĭa-khí tâng pâng',
    ('nâng m̄-bó̤ cṳ̆ pău, cṳ̆ khì', 'one should not throw himself away in a fit of rage.', '444'): 'nâng m̄-hó̤ cṳ̆ pău, cṳ̆ khì',
    ('cêk tīo pê tŏ̤ lṳ́ sin tèng', 'there is one crawling upon you.', '445'): 'cêk tîo pê tŏ̤ lṳ́ sin tèng',
    ('nŏ̤ pôiⁿ tîeh péⁿ cài, cē m̄ péⁿ cài cū àiⁿ tăng-thâu-áu', 'you must lade in equally on either side, if you do not it will tip to one side.', '445'): 'nŏ̤ pôiⁿ tîeh pêⁿ cài, cē m̄ pêⁿ cài cū àiⁿ tăng-thâu-áu',
    ('īa si àiⁿ pèⁿ i kâi pn̄g-úaⁿ-thâu li i căi tit hàuⁿ?', 'How can he consent to having the tidbit that caps his bowl of rice taken away?', '445'): 'īa sĭ àiⁿ pèⁿ i kâi pn̄g-úaⁿ-thâu li i căi tit hàuⁿ ?',
    ('khîeh cīⁿ khṳ̀ bói pēⁿ', 'to purchase illness, to smoke opium.', '446'): 'khîeh cîⁿ khṳ̀ bói pēⁿ',
    ('pēⁿ hó̤ lí̤o', 'has recovered.', '446'): 'pēⁿ hó̤ lío',
    ('hek pêk hun mêng', 'black and white distinctly divided.', '447'): 'hek pêh hun mêng',
    ('lṳ́ màiⁿpeh chîeⁿ, peh piah', 'do not clamber over the walls.', '447'): 'lṳ́ màiⁿ peh chîeⁿ, peh piah',
    ('m̄ khéng cêk phe', 'not so few as a hundred.', '447'): 'm̄ khéng cêk peh',
    ('tìeⁿ khí lâi mâk-ciu kaik-kiak pêh', 'bulged out his eyeballs.', '447'): 'tìeⁿ khí lâi mâk-ciu kiak-kiak pêh',
    ('kiē bw̆n', 'sedan curtains.', '45'): 'kīe bw̆n',
    ('pàng kò̤ ŭ-pĭ put ngô̤', 'put it aside in readiness for an emergency.', '450'): 'pàng kò̤ ṳ̆-pĭ put ngô̤',
    ('tôaⁿ pî-pê', 'play the viol.', '450'): 'tôaⁿ pî-pê thâng pî-pê',
    ('ci-pĭ', 'to hide from observation.', '451'): 'cia-pĭ',
    ('i thì tīo piⁿ khṳ̤̀ cò̤ hûe-sīeⁿ', 'he shaved off his queue and became a priest.', '451'): 'i thì tīo piⁿ khṳ̀ cò̤ hûe-sīeⁿ',
    ('i tâng sò̤i bōi khṳt nâng ûi pĭ', 'she was sold as a slave in early childhood.', '451'): 'i tâng sòi bōi khṳt nâng ûi pĭ',
    ('pǐ', 'A maid-servant; unmarried female slaves.', '451'): 'pĭ',
    ('pǐ', 'To ascend high places; ascent to a palace or court.', '451'): 'pĭ',
    ('pǐ', 'To shade; to screen; obscured.', '451'): 'pĭ',
    ('pǐ', 'Trouble, mischief.', '451'): 'pĭ',
    ('guêh píaⁿ', 'cakes made at the full of the eighth moon and used in worshipping it.', '452'): 'gûeh píaⁿ',
    ('piàng', 'To slap; to pound; to rap.', '453'): 'pìang',
    ('koiⁿ-hâu áu ki píen-taⁿ', 'carried a flat carrying pole over his shoulder.', '454'): 'koiⁿ-thâu áu ki píen-taⁿ',
    ('put pĭon cìeⁿ-seⁿ cò̤', 'it is inexpedient to do so.', '454'): 'put pĭen cìeⁿ-seⁿ cò̤',
    ('húe lí-hẃn piu chut lâi', 'the flames burst forth incessantly.', '457'): 'húe lí-kẃn piu chut lâi',
    ('i hàm kĭe-po-thâu lâi mn̄g', 'he told the chief chair-bearer to come and inquire.', '458'): 'i hàm kĭe-po-thâu lâi m̄ng',
    ('m̄ hó̤ khah méⁿ póiⁿ cìaⁿ ŏ̤i kàu kò̤', 'do not turn them over too soon, and then they will cohere in one piece.', '460'): 'm̄ hó̤ khah méⁿ póiⁿ cìaⁿ ŏi kàu kò̤',
    ('huang hiah, éng būe hiah, hía cûn tó̤ pong lío', 'after the wind has ceased and before the waves have gone down, the pitching of the vessel is hardest for people to bear.', '461'): 'huang hiah, éng būe hiah, hía cûn tó̤ pong lío, nâng kèng kang-khó',
    ('thiⁿ cīeⁿ ŭ pó̤, jît gûeh cheⁿ sîn tī cīeⁿ ŭ pó̤ hàu cṳ́ tong chîn', 'what is most highly prized in the heavens are the sun, the moon, the stars and the gods: what is most valuable among earthly things are filial sons and loyal courtiers.', '461'): 'thiⁿ cīeⁿ ŭ pó̤, jît gûeh cheⁿ sîn: tī cīeⁿ ŭ pó̤ ：hàu cṳ́ tong chîn',
    ('câh p̤ô̤h', 'to set up a weir.', '462'): 'câh pô̤h',
    ('kŏ sîn pó̤-īu phêng-ang', 'trust the gods to keep in safety.', '462'): 'kŏ sîn pó̤-ĭu phêng-ang',
    ('màiⁿ thiu kah pô̤h', 'do not plane it too thin.', '463'): 'màiⁿ thiu khah pô̤h',
    ('pû hua', 'a square shallow wooden dipper.', '463'): 'pû hia',
    ('pùaⁿ guêh', 'half a month.', '464'): 'pùaⁿ gûeh',
    ('îaⁿ-pûaⁿ cap to̤ ̆tī-kò̤?', 'Where is the camp set?', '464'): 'îaⁿ-pûaⁿ cap tŏ̤ tī-kò̤ ?',
    ('sī pûah tîeh im pue, a sĭ îang pue, a sĭ sèng pue?', 'When you tossed the two bamboo-roots did they fall with the flat sides downward, or with the convex sides downward or with one flat side and one convex side downward?', '465'): 'sĭ pûah tîeh im pue, a sĭ îang pue, a sĭ sèng pue ?',
    ('bô̤ pūe', 'no repayment for losses.', '466'): 'bô̤ pûe',
    ('hṳ́ kâi sĭ mîaⁿ châk, tîeh lô̤h kha-câk', 'that is a famous robber, and he must be fettered.', '47'): 'hṳ́ kâi sĭ mîaⁿ châk, tîeh lô̤h kha-câh',
    ('cia máng-phè', 'wear a veil.', '472'): 'cia măng-phè',
    ('phau tīo sūaīⁿ phûe', 'shave off the rind of a mango.', '472'): 'phau tīo sūaiⁿ phûe',
    ('phàu thâu sì khùi to hak ŭ', 'has long and short robes for all the four seasons.', '472'): 'phâu thâu sì-khùi to hak ŭ',
    ('phău bṳ̆n cong sin', 'I can never forgive it.', '472'): 'phău hṳ̆n cong sin',
    ('phǎu', 'To feel; to have in the heart; to adhere.', '472'): 'phău',
    ('suāiⁿ-phau', 'a knife used in paring mangoes.', '472'): 'sūaiⁿ-phau',
    ('i lâi chíaⁿ kâi thiap sĭ sía "pheng mêng hāu kà"', 'his card of invitation said, "the tea is made and we await your instructions."', '473'): 'i lâi chíaⁿ kâi thiap sĭ sía “ pheng mêng hāu kà ”',
    ('i mîaⁿ-ke pheng-thîo chài-bǔ', 'she is skillful in concocting food.', '473'): 'i mîaⁿ-ke pheng-thîo chài-bŭ',
    ('bô̤ tham i kâi kāu phìaⁿ', 'do not covet a large dower.', '475'): 'bô̤ tham i kâi kău phìaⁿ',
    ('cía cū sǐ hì-pêⁿ-téng kâi ūe-pêh-phīⁿ kâi', 'this is the buffoon in the theatre (and has his nose painted white).', '475'): 'cía cū sĭ hì-pêⁿ-téng kâi ūe-pêh-phīⁿ kâi',
    ('i kâi phiah pēⁿ m̄-hō̤', 'he has vicious propensities.', '475'): 'i kâi phiah pēⁿ-m̄-hó̤',
    ('khṳt i kâi búe cē phîak, uâng cū pûah lô̤h khṳ̀', 'one blow from his tail would knock a person down.', '475'): 'khṳt i kâi búe cē phîak, nâng cū pûah lô̤h khṳ̀',
    ('phīⁿ tîeh phang cǎi', 'smelled very fragrant.', '475'): 'phīⁿ tîeh phang căi',
    ('châng phîe li hó̤, m̄ căi ău-lâi kak kúe căi-seⁿ?', 'The young grain is in fine condition, but we do not know how it will be when it hereafter comes to head up.', '476'): 'châng phîe li hó̤, m̄ cai ău-lâi kak kúe căi-seⁿ ?',
    ('cía sĭ cang ˘nng khṳ̀ phîn cîeh-thâu', 'this is pitting an egg against a stone.', '477'): 'cía sĭ cang n̆ng khṳ̀ phîn cîeh-thâu',
    ('khîeh kò̤ cng-kŏ̤ khṳ̀ phîn i', 'took a brickbat, and hit him with it.', '477'): 'khîeh kò̤ cng-kò̤ khṳ̀ phîn i',
    ('khṳ̀ phô̤k-tîeh i tú-tú tó̤ cîah a-phìen', 'went and espied him just when he was smoking opium.', '479'): 'khṳ̀ phôk-tîeh i tú-tú tó̤ cîah a-phìen',
    ('phōiⁿ', 'or pōiⁿ. To manage, to attend to, to prepare, to provide, to go on with, to transact business; to act as a factor.', '479'): 'phōiⁿ or pōiⁿ',
    ('cí ciah cûn cài ŭ jîeh cōi tàⁿ?', 'How many piculs does this boat carry?', '48'): 'cí ciah cûn cài ŭ jîeh cōi tàⁿ ？',
    ('lṳ́ câi sĭeⁿ', 'think again.', '48'): 'lṳ́ cài sĭeⁿ',
    ('cêk phìeⁿ phô̤ sim', 'a motherly heart.', '480'): 'cêk phìen phô̤ sim',
    ('nŏ̤ cîah cûn sie phòng', 'the two vessels collided.', '480'): 'nŏ̤ ciah cûn sie phòng',
    ('pho̤h', 'To cleave at a blow; to cut with a heavy stroke.', '480'): 'phún',
    ('phû-thî-chīu', 'the seeds of the pipul tree, used as beads.', '481'): 'phû-thî-cí',
    ('phū-chàu', 'light minded; without stability or dignity.', '481'): 'phû chàu',
    ('c̤̀o kâi phue tŏ̤-kò̤, būe cêng sie', 'have the pot tery made, but have not yet baked it.', '482'): 'cò̤ kâi phue tŏ̤-kò̤, būe cêng sie',
    ('kâi sĭ tṳ phŭaⁿ hóⁿ mî', 'it is like to the dog offering himself to the tiger as a bed-fellow.', '482'): 'kâi sĭ tṳ phŭaⁿ hóⁿ mîn',
    ('phùe m̄ cieⁿ', 'it does not fit.', '483'): 'phùe m̄ cĭeⁿ',
    ('cí kháu phûn kih ŭ kâi tûn', 'this grave has a terrace built up before it.', '484'): 'cí khán phûn kih ŭ kâi tûn',
    ('kak ̤̂oh kâi ô̤h-keng lăi to ŭ phẁn-keng tî', 'every college has the semi-circular pool within its grounds.', '484'): 'kak ô̤h kâi ô̤h-keng lăi to ŭ phẁn-keng tî',
    ('phùn cho̤h cúi lo̤h khṳ̀', 'dash some water on it.', '484'): 'phùn cho̤h cúi lô̤h khṳ̀',
    ('phŵn bùi', 'fare; travelling expenses.', '484'): 'phŵn hùi',
    ('saⁿ hùe phŏ̤ nŏ̤t', 'had two children in three years.', '485'): 'saⁿ hùe phŏ̤ nŏ̤',
    ('chíu tho̤h hiang sai', 'she leaned her chin on her hand.', '486'): 'chíu thoh hiang sai',
    ('cía put kùe sĭ sám-kháu kâi mûeh-kĭaⁿ', "this is something to peck at merely, it is not a thing to satisfy one's hunger upon.", '488'): 'cía put kùe sĭ sám-kháu kâi mûeh-kĭaⁿ, m̄ sĭ hó̤ cîah pá kâi mûeh-kĭaⁿ',
    ('khṳ̀ sam', 'to saw logs.', '488'): 'kṳ̀ sam',
    ('i kâi to̤ lō sêk căi', 'he handles his knife with dexterity, cutting downward rapidly and incessantly.', '489'): 'i kâi to̤ lō sêk căi , sap-sap-sap lí-kẃn lô̤h',
    ('boí khṳ̀ pàng seⁿ', 'buy living creatures in order to set them free, an act considered to be meritorious.', '490'): 'bói khṳ̀ pàng seⁿ',
    ('khîa sàu-síu-pèⁿ', 'pound him with the broom-handle.', '490'): 'khîa sàu-síu-pèⁿ bût i',
    ('kin-nî kâi tāu seⁿ cōi căi, kū-nî cn̂g kâi bŏⁿ seⁿ', 'the peas are very productive this year, last year they did not bear at all.', '490'): 'kin-nî kâi tāu seⁿ cōi căi, kū-nî cn̂g kâi bŏi seⁿ',
    ('thiⁿ seⁿ cṳ̄-jîen', 'a natural production.', '490'): 'thiⁿ seⁿ cṳ̆-jîen',
    ('tōa se', 'to warp yarn.', '490'): 'tŏa se',
    ('úang i pĕ-bó̤ seⁿ i kàu cìaⁿ tōa!', 'It is a pity that his parents reared him!', '490'): 'úang i pĕ-bó̤ seⁿ i kàu cìeⁿ tōa!',
    ('cău-hùe kuaⁿ khai-sek i', 'fortunately the magistrate released him, and did not keep him under arrest.', '492'): 'cău-hùe kuaⁿ khai-sek i, bô̤ ah i',
    ('mâiⁿ-mîaⁿ, mût sèⁿ', "to conceal one's name.", '492'): 'mâi-mîaⁿ, mût sèⁿ',
    ('sek ngŏ̤ ŭ nâng-khek lâi', 'just then a visitor came.', '493'): 'sek ngŏ̤ ŭ nâng-kheh lâi',
    ('cō̤ sèng sì', 'on the winning side.', '494'): 'cŏ̤ sèng sì',
    ('m̄ sen̂g phìen tn̄g', 'not amounting to a wholesale packet.', '495'): 'm̄ sêng phìen tn̄g',
    ('i kâi nūaⁿ seⁿ si', 'his saliva is ropy.', '496'): 'i kâi nŭa seⁿ si',
    ('i būe hío sèⁿ sí mn̂g', 'he does not yet know in which way safety or danger lies.', '497'): 'i būe hío sèⁿ sí m̂ng',
    ('jûah thiⁿ-sî si kûe-sìⁿ, chìn thiⁿ-sî si húe-thang', 'in hot weather give away palm-leaf fans, in cold weather, braziers.', '497'): '̇jûah thiⁿ-sî si kûe-sìⁿ, chìn thiⁿ-sî si húe-thang',
    ('si ṳn khṳt', 'favor him.', '497'): 'si ṳn khṳt i',
    ('àiⁿ sí, bōi tit sí', 'is anxious to die as soon as possible.', '497'): 'àiⁿ sí, bŏi tit sí',
    ('i kâi uá tī-tîang kâi sì?', 'Whose influence does he rely on?', '498'): 'i kâi úa tī-tiang kâi sì?',
    ('sì cieⁿ, sì thói', 'the limbs; the whole body.', '498'): 'sì ciⁿ, sì thói',
    ('sì lō nĕ tît-tit̂', 'straight roads in all directions.', '498'): 'sì lō nĕ tît-tît',
    ('sì tāi thien ûang', 'four demon kings whose images are placed at the doors of monasteries.', '498'): 'sì tăi thien ûang',
    ('cêk ngân kì chut sì bé lâng tai', 'when a word is once spoken four horses cannot bring it back.', '499'): 'cêk ngân kì chut sì bé lâng tui',
    ('cīu-sî', 'straight-way.', '499'): 'cĭu-sî',
    ('ngē sî i', 'firmly declined his offer.', '499'): 'ngĕ sî i',
    ('suî-sî', 'immediately.', '499'): 'sûi-sî',
    ('cí tīo lō sia lô̤h kàu khoi-kîⁿ', 'this road slopes down to the bank of the river.', '500'): 'cí tîo lō sia lô̤h kàu khoi-kîⁿ',
    ('sĭ hó̤ sī khiap cò̤ cē tŏ̤ cí', 'good or bad, they are all here together.', '500'): 'sĭ hó̤ sĭ khiap cò̤ cē tŏ̤ cí',
    ('taù ki sìⁿ pèⁿ', 'put a handle on a fan.', '500'): 'tàu ki sìⁿ pèⁿ',
    ('tuí huang-sìⁿ', 'pull the punka.', '500'): 'túi huang-sìⁿ',
    ('châng-tī sía lô̤h am-īⁿ', 'you may give your fields to a monastery, but you cannot thereafter beg a bowl of porridge from the priests.', '501'): 'châng-tī sía lô̤h am-īⁿ, kio hûe-sīeⁿ khṳt bô̤ úaⁿ ám cîah',
    ('tāi-ì', 'write out a synopsis.', '501'): 'sía kâi tăi-ì',
    ('cía tîeh tāng sīa i', 'he must be largely rewarded for this.', '502'): 'cía tîeh tăng sīa i',
    ('sîaⁿ chîaⁿ', 'the city wall.', '502'): 'sîaⁿ chîeⁿ',
    ('sĭ sīa bé-cìⁿ a sīa oō-cìⁿ?', 'Are they shooting with arrows used by the cavalry or with those used by the infantry?', '502'): 'sĭ sīa bé-cìⁿ a sīa pō-cìⁿ ?',
    ('cía kâi hŵn-lío put-siak cîah, lṳ́ àiⁿ cîah sĭm-mûeh?', 'If you will not eat this, what then are you going to eat?', '503'): 'cí kâi hŵn-lío put-siak cîah, lṳ́ àiⁿ cîah sĭm-mûeh ?',
    ('mâk sang mâk siap', 'dreadfully sleepy.', '505'): 'mâk sng mâk siap',
    ('síe-cíe', 'the young lady (of high rank).', '506'): 'síe-cía',
    ('ka-lâuh lío bŏi sieⁿ bŏi sún', 'was not injured at all by being dropped.', '507'): 'ka-lâuh lio bŏi sieⁿ bŏi sún',
    ('i chìo kâu thâi sí nâng míen sîeⁿ mīaⁿ', 'they are so powerful that they may even kill a person and make no compensation for his life.', '507'): 'i chìo kàu thâi sí nâng míen sîeⁿ mīaⁿ',
    ('sĭeⁿ?', 'What do you think about it.', '508'): 'lṳ́ cò̤̀-nî sĭeⁿ ?',
    ('pâk càng kâi tek-hîeh ēng ke kùe jú hó̤, bŏ̤i chàu tek-hîeh bī', 'the bamboo leaves used in wrapping dumplings are better after having been used several times, for then they will not impart a taste to the dumpling.', '51'): 'pâk càng kâi tek-hîeh ēng ke kùe jú hó̤, bŏi chàu tek-hîeh bī',
    ('i kâi sim hiàng tŏ̤ i kò̤', 'her heart inclines toward him.', '510'): 'i kâi sim hìang tŏ̤ i kò̤',
    ('sim-kuaⁿ-thâh pôk-pôk-thìo', 'heart throbs violently.', '510'): 'sim-kuaⁿ-thâu pôk-pôk-thìo',
    ('síe-sim; sôi-sim', 'carefully; attentively; sedulous.', '510'): 'síe-sim; sòi-sim',
    ('sím-phŵn', 'to examine the evidence and pronounce judgment.', '510'): 'sím-phẁn',
    ('ēn cĭn sim-ki', 'take the utmost pains.', '510'): 'ēng cĭn sim-ki',
    ('sĭm sī ŏi', 'is remarkably able.', '511'): 'sĭm sĭ ŏi',
    ('uē cn̂g sin', 'draw a full length portrait.', '511'): 'ūe cn̂g sin',
    ('tâng-sin cĭeⁿ to̤-thui, kîaⁿ hûe lō, lô̤h iû thng', 'the spirit-medium ascends a ladder of knives, walks over a bed of coals, and plunges into hot oil.', '512'): 'tâng-sin cĭeⁿ to̤-thui, kîaⁿ hûe lō, lô̤h îu thng',
    ('cí kâi sìn-ńng sen̂g-sim căi', 'this devotee is very sincere.', '513'): 'cí kâi sìn-ńng sêng-sim căi',
    ('cía kâi nâng hó̤ ēng sîn', 'this person has his wits about him.', '513'): 'cí kâi nâng hó̤ ēng sîn',
    ('cēⁿ-ūn ngŵn-sîn', 'compose your spirit; calm yourself.', '513'): 'cĕⁿ-ūn ngŵn-sîn',
    ('sîn hut; native and foreign gods', 'native sages and Buddha.', '513'): 'sîn-hut',
    ('sîn hué', 'a fire ball; a bright Jack-o-lantern.', '513'): 'sîn húe',
    ('sîn sìeⁿ; images', 'idols.', '513'): 'sîn sìeⁿ',
    ('sîn-hûn', 'the soul, before or after death.', '513'): 'sîn-hûn, íang sîn',
    ('teh kî kaî sṳ̄ sĭ lâu sîn căi', 'chess is a thing that taxes the mind.', '513'): 'teh kî kâi sṳ̄ sĭ lâu sîn căi',
    ('thiah-khui huang-tan̂g khîeh sìn lâi thóiⁿ', 'open the envelope and take out the letter and look at it.', '513'): 'thiah-khui huang-tâng khîeh sìn lâi thóiⁿ',
    ('i kâi a-pĕ íⁿ-keng pín kùe put sìo kâi, ṳ̆ i bô̤ kang', 'his father has already legally disowned him, and has nothing to do with him.', '515'): 'i kâi a-pĕ íⁿ-keng pín kùe put sìo kâi, ṳ́ i bô̤ kang',
    ('i kâi kíaⁿ, tōa kâi cū hàn-sŭn, jī kâi cū put-sìo', 'of his sons, the eldest is filial, and the next to the eldest is unfilial.', '515'): 'i kâi kíaⁿ, tōa kâi cū hàu-sŭn, jī kâi cū put-sìo',
    ('sio-chê cng-mûeh kâi pbìe', 'a search-warrant, authorizing a search for stolen goods.', '515'): 'sio-chê cng-mûeh kâi phìe',
    ('pêh-sioh pêh-sĭoh', 'pale, colorless.', '516'): 'pêh-sioh pêh-sioh',
    ('àⁿ t̤̆o i sît e', 'hovered under her wings.', '517'): 'àⁿ tŏ̤ i sît ĕ',
    ('i cò̤ cêk síu sĭ', 'he composed a poem.', '518'): 'i cò̤ cêk síu si',
    ('i àiⁿ nā kò̤ⁿ síu-cak', "she wishes to stay in her husband's family, and remain his widow.", '518'): 'i àiⁿ nā kò̤ síu-cak',
    ('siu ngṳ̂n, sîu cîⁿ', 'collect money from debtors; take in coin.', '518'): 'siu ngṳ̂n, siu cîⁿ',
    ('siu-hó̤k nâng sim', "win people's hearts.", '518'): 'siu-hôk nâng sim',
    ('cí kâi kuaⁿ ŭ sĭu lṳ́ a bô̤?', 'Does this magistrate accept bribes?', '519'): 'cí kâi kuaⁿ ŭ sĭu ĭu a bô̤ ?',
    ('i sĭ kâi huang mn̂g sìu sṳ̄', 'he is one who has earned, not bought, his degree.', '519'): 'i sĭ kâi huang mn̂g sìu sṳ̆',
    ('seⁿ lâi sìu-līu sìu-līu', 'has naturally a very graceful bearing.', '519'): 'seⁿ kâi sìu-līu sìu-līu',
    ('sìu sṳ̄', 'an accomplished scholar.', '519'): 'sìu sṳ̆',
    ('pin-lô̤ cap maìⁿ phùi cêk saⁿ', 'do not get betel juice all over your jacket.', '52'): 'pin-lô̤ cap màiⁿ phùi cêk saⁿ',
    ('pàng tŏ̤ tŏiⁿ saⁿ câng', 'put it on the third shelf.', '52'): 'peh kàu tŏiⁿ ngŏ câng',
    ('cía put kùe sĭ soih phûe phāng kâi', 'this is nothing more than filling up a narrow space between two other graves.', '522'): 'cía put kùe sĭ soih phûn phāng kâi',
    ('hàm i soiⁿ kiâⁿ', 'tell him to go first.', '522'): 'hàm i soiⁿ kîaⁿ',
    ('tâng soiⁿ tō̤ jŭi lô̤h lâî kâi', 'handed down from former generations.', '522'): 'tâng soiⁿ tō̤ jŭi lô̤h lâi kâi',
    ('i kâi thâu-mô̤ⁿ phô̤ng-phô̤ng song-song', 'her hair is all flying at loose ends.', '524'): 'i kâi thâu-mô̤ⁿ phông-phông song-song',
    ('iông-sôk kâi nâng', 'the vulgar.', '524'): 'îong-sôk kâi nâng',
    ('pī i só̤ pek a m̄ sĭ?', 'Was urged to it by him was he not?', '525'): 'pĭ i só̤ pek a m̄ sĭ ?',
    ('só̤ mn̂g', 'lock the door.', '525'): 'só̤ m̂ng',
    ('só̤ sīeⁿ kâi cū tùi', 'what I thought proves to be the case.', '525'): 'só̤ sĭeⁿ kâi cū tùi',
    ('cong su u pò̤-èng', 'at last there must be a recompense.', '526'): 'cong su ŭ pò̤-èng',
    ('cĭeⁿ sò̤ khṳ̀ kàing hûang-tì', 'lay a protest before the emperor.', '526'): 'cĭeⁿ sò̤ khṳ̀ kàng hûang-tì',
    ('sŏ̤ mn̂g châk', 'robbers who force entrance into dwellings.', '526'): 'sŏ̤ m̂ng châk',
    ('i en̂g kâi m̄ siang-sù nâng', "she does not overlook people's faults at all.", '527'): 'i cn̂g kâi m̄ siang-sù nâng',
    ('cṳ̄ í̤n suaⁿ lîm', 'to retire into obscurity; seek retirement among hills.', '529'): 'cṳ̆ ṳ́n suaⁿ lîm',
    ('cíu cau', 'sâh cíu kâi cau; distiller’s grains.', '53'): 'cíu cau; sâh cíu kâi cau',
    ('suaⁿ phiⁿ thâu', 'a headland.', '530'): 'suaⁿ phīⁿ thâu',
    ('cêk kîa sùaⁿ', 'a ball of thread.', '531'): 'cêk kîu sùaⁿ',
    ('saⁿ iam nê-sùaⁿ', 'a three storied official umbrella.', '531'): 'saⁿ ĭam nê-sùaⁿ',
    ('huâng-tì ŭ cí khṳ̀ suang-tĭo i', 'the emperor sent to summon him.', '532'): 'hûang-tì ŭ cí khṳ̀ suang-tĭo i',
    ('i khṳ̤t i khó kàu cn̂g kâi sûe-sûe, m̄ ká tin-tăng', 'she was harassed by him until she was wholly worn out, and could do nothing.', '533'): 'i khṳt i khó kàu cn̂g kâi sûe-sûe, m̄ ká tin-tăng',
    ('hṳ́ téng cò̤ tîo lāu-bó̤, màiⁿ khṳt lîm-cíⁿ cúi sûi lò̤h lâi', 'make an eaves-trough above, and not let the water from the eaves drip down.', '534'): 'hṳ́ téng cò̤ tîo lāu-bó̤, màiⁿ khṳt lîm-cíⁿ cúi sûi lô̤h lâi',
    ('hṳ́-kò̤ ŭ sûn-leng hùe tó̤ sûn-chê', 'there are policemen there looking after it.', '535'): 'hṳ́-kò̤ ŭ sûn-teng hùe tó̤ sûn-chê',
    ('sún cîn khṳ̀', 'the tenon has broken off.', '535'): 'sún cîh khṳ̀',
    ('sún khùaⁿ cū àiⁿ ie-ló', 'if the tenons are not tightly set it will rattle.', '535'): 'sún khùaⁿ cū àiⁿ ĭe-ló',
    ('ciah eng sṳ̂t lô̤h lâi tìo koi-kínⁿ', 'a hawk swooped down and carried off a chicken.', '537'): 'ciah eng sût lô̤h lâi tìo koi-kíaⁿ',
    ('sĭu kùe hṳ̂ang-sĭang kâi ṳn-sṳ̀', 'have experienced the kindness of the emperor.', '537'): 'sĭu kùe hûang-sĭang kâi ṳn-sṳ̀',
    ('sṳ-bûn sâu tī', 'put scholarship to ignoble uses.', '537'): 'sṳ-bûn sàu tī',
    ('sṳ-nîe in̄ tn̄g kè, thó cîⁿ àiⁿ sie mēⁿ', 'when the price is not fixed by previous arrangement, there is a quarrel when payday comes.', '537'): 'sṳ-nîe m̄ tn̆g kè, thó cîⁿ àiⁿ sie mēⁿ',
    ('sṳ̀ ṳ̆ téng-tài', 'gave him permission to wear a button; rewarded him by giving him rank without office.', '537'): 'sṳ̀ ŭ téng-tài',
    ('thăi-sṳ́-tŏ̤iⁿ', 'a Hanlin graduate.', '537'): 'thăi-sṳ́-tŏiⁿ',
    ('cí kâi suaⁿ sĭ tn̆g sṳ̆ a m̄ sí?', 'This mountaian is cut off from the mainland is it not?', '538'): 'cí kâi suaⁿ sĭ tn̆g sṳ̆ a m̄ sĭ',
    ('cía m̄ cì sṳ̄', 'this does not help the matter.', '539'): 'cín m̄ cì sṳ̄',
    ('hàm i kâi ău sṳ̄ tîeh khṳ̀ ŭ-pĭ', 'tell him that he must prepare for the consequences.', '539'): 'hàm i kâi ău sṳ̄ tîeh khṳ̀ ṳ̆-pĭ',
    ('sī hŏng che sṳ̄ lâi kâi', 'is one sent on special business.', '539'): 'sĭ hŏng che sṳ̄ lâi kâi',
    ('cău hŭam', 'an escaped criminal.', '54'): 'cáu hŭam',
    ('tāⁿ-tăⁿ nē kau-chap cū hó̤', 'to be merely civil in intercourse with them is all that is desirable.', '542'): 'tăⁿ-tăⁿ nē kau-chap cū hó̤',
    ('cí kâi nâng hó̤ siang-sìn, úa kâi cîⁿ ngṳ̂n to sĭ kìa-tah', 'this person is trustworthy, and I send my money by him.', '543'): 'cí kâi nâng hó̤ siang-sìn, úa kâi cîⁿ ngṳ̂n to sĭ kìa-tah i',
    ('cò̤ cíau-sîah kẃn-tăi i', 'entertained him by making a feast in his honor.', '544'): 'cò̤ cíu-sîah kẃn-tăi i',
    ('cièⁿ-seⁿ sǹg sĭ khṳt i tam-gō khṳ̀', 'it seems that we have depended on him to our cost; he has apparently failed to carry out his part in the plan.', '545'): 'cìeⁿ-seⁿ sǹg sĭ khṳt i tam-gō khṳ̀',
    ('cía cìⁿ sĭ cìm tâk îeh kâi īa sĭ khṳt cía tâk cìⁿ sīa tîeh cū sí', 'this arrow is one that has been sleeped in poison: if you are hit by a poisoned arrow you will die.', '545'): 'cía cìⁿ sĭ cìm tâk îeh kâi：īa sĭ khṳt cía tâk cìⁿ sīa tîeh cū sí',
    ('lṳ́ hó̤ tâk î tâk jī tàⁿ úa thiaⁿ', 'you take up the heads one by one in their order and recite them to me.', '545'): 'lṳ́ hó̤ tâk it tâk jī tàⁿ úa thiaⁿ',
    ('tâk kâ tâk kâi to kìⁿ cheng-chó̤ lío', 'they are all recorded, in their order.', '545'): 'tâk kâi tâk kâi to kìⁿ cheng-chó̤ lío',
    ('tîeh ēng ngṳ̂n-khì lâi kehh tīo i kâi tâk hueh', 'must use a silver instrument to scrape off the poisoned blood.', '545'): 'tîeh ēng ngṳ̂n-khì lâi kheh tīo i kâi tâk hueh',
    ('i ke tang ŭ kâi lău bó̤ tŏ̤-kò̤', 'he has an old mother at home.', '546'): 'i ke tang ŭ kâi i lău bó̤ tŏ̤-kò̤',
    ('bó̤i lâi pun a-noⁿ-kíaⁿ hùe táng lō', 'buy some thing to take to the children when I go home.', '547'): 'bói lâi pun a-noⁿ-kíaⁿ hùe táng lō',
    ('cí kúi nî kâi hun-kuah ē-ē khṳt sng tàng sīo khṳ̀', 'these last few years, the potato vines have been repeatedly injured by the frost.', '547'): 'cí kúi nî kâi hun-kuah ē-ē khṳt sng tàng tīo khṳ̀',
    ('sng cē tàng chīu-hîeh cū n̂ng', 'the leaves turn yellow when the frost touches them.', '547'): 'sng cē tàng chīu-hîeh cū n̂g',
    ('tak tâng', 'a section of the trunk of a bamboo used as a measure, and holding a pint.', '548'): 'tek tâng',
    ('thiaⁿ kìaⁿ hn̆g-hn̆g lûi tâng', 'hear the thunder afar off.', '548'): 'thiaⁿ kìⁿ hn̆g-hn̆g lûi tâng',
    ('àiⁿ ki tâng a m̆?', 'Do you want a fine line of brass around it?', '548'): 'àiⁿ ki tâng ăm ?',
    ('bô̤ saⁿ nít tăng', 'scarcely any weight.', '549'): 'bô̤ saⁿ níe tăng',
    ('cang tăng khw̆n hù i', 'give him great authority.', '549'): 'tăng khṳ̀ tìm',
    ('i kâi cò̤ sṳ̄ hùang-hùang tăng-tăng', 'his behaviour is most reckless, unmannerly and lawless.', '549'): 'i kâi cò̤ sṳ̄ hùang-hùang tăng-tăng, bô̤ lói bô̤ huap',
    ('tī-hng khah khùang-tăng', 'the place is too wild and wide, and is not snug and cozy.', '549'): 'tī-hng khah khùang-tăng, m̄ kín-kauh',
    ('cí ciah thīⁿ-saⁿ-chia sĭ tī-tîang cău-khí kâi?', 'Who invented this sewing machine?', '55'): 'cí ciah thīⁿ-saⁿ-chia sĭ tī-tîang cău-khí kâi ？',
    ('cîah ce pó cêk ak', 'fast as an offset to wickedness.', '55'): 'cîah ce pó cek ak',
    ('i cē lāu cū-lău-tien-táu', 'in growing old he has grown forgetful.', '550'): 'i cē lău cū lău-tien-táu',
    ('táu cêk kâi ûant-pó̤ cìaⁿ ēng cò̤ kâi gûeh', 'get a bar of silver exchanged for small coin, and it is spent in a month.', '550'): 'táu cêk kâi ûang-pó̤ cìaⁿ ēng cò̤ kâi gûeh',
    ('hàm nŏ̤ pang lâi sie tàu', 'call two companies of performers to emulate each other.', '551'): 'hàm nŏ̤ pang lâi sie tàu hì',
    ('taù thâk cṳ', 'strive to excel each other in study.', '551'): 'tàu thâk cṳ',
    ('khai-tău kàu mêng-pêh mêng-pêh khṳ̂t i thiaⁿ', 'set the correct method plainly before him.', '552'): 'khai-tău kàu mêng-pêh mêng-pêh khṳt i thiaⁿ',
    ('lṳ́ màiⁿ tŏ̤ tèⁿ sì tèⁿ ûah', 'you need not pretend to be more dead than alive.', '553'): 'lṳ́ màiⁿ tŏ̤ tèⁿ sí tèⁿ ûah',
    ('cìe nâng-teng phàin cîⁿ', 'apportion the amount to be contributed according to the number of contributors.', '555'): 'cìe nâng-teng phài cîⁿ',
    ('huang teng', 'hun teng; an opium lamp.', '555'): 'huang teng, hun teng',
    ('tē-teng cîⁿ-nîe', 'the land revenue estimated in money.', '555'): 'tī-teng cîⁿ-nîe',
    ('lît-téng thûi, lî-téng pûaⁿ, teńg pûaⁿ so̤h, lî-téng nău', 'the brass weight, the brass pan, the cords attached to the pan, and the two holding cords of Chinese money scales.', '556'): 'lî-téng thûi, lî-téng pûaⁿ, téng pûaⁿ so̤h, lî-téng nău',
    ('teńg tît chìn, bô̤ kio bô̤ bî', 'poise the scale yard horizontally neither inclining upward nor downward.', '556'): 'téng tît chìn, bô̤ khio bô̤ bî',
    ('tèng kṳ́-jîn lío cū tèng cìu-sṳ̄', 'having taken the degree of Master of Arts, he gained that of Doctor of Laws.', '556'): 'tèng kṳ́-jîn lío cū tèng cìn-sṳ̆',
    ('tèng pit khṳ̀', 'cannot drive the nail in.', '556'): 'tèng m̄ lô̤h',
    ('i kâi nâng tēng-ten̄g nē', 'he is very tall and straight.', '557'): 'i kâi nâng tēng-tēng nē',
    ('ŭ nâng cang kha-ău-teⁿ tâh bé-tâh-tèng; ŭ nâng cang kha-ău-tenn tâh bé-tâh-tèng', 'some people put the toe in the stirrup, and some the heel.', '557'): 'ŭ nâng cang kha-ău-teⁿ tâh bé-tâh-tèng',
    ('peh-sèⁿ khṳ̀ kìⁿ kuaⁿ sĭ cheng ka-kī cò̤ "síe ti"', 'common people who go before a magistrate speak of themselves as "humble selves." cí khí sṳ̄ sĭ ŭ ti; this is something that really happens.', '558'): 'peh-sèⁿ khṳ̀ kìⁿ kuaⁿ sĭ cheng ka-kī cò̤ “síe ti”',
    ('pun tī-tiâng?', 'To whom did you give it?', '559'): 'pun tī-tîang',
    ('tì-ūi thŵn khuⁿt tī-tîang?', 'To whom does the throne descend?', '559'): 'tì-ūi thŵn khṳt tī-tîang',
    ('cí kâi bûn-cuⁿ sĭ àiⁿ tī kàu séⁿ-sîaⁿ', 'this dispatch is to be sent to Canton.', '560'): 'cí kâi bûn-cṳ sĭ àiⁿ tī kàu séⁿ-sîaⁿ',
    ('lṳ́ cò̤ sṳ̄ mâiⁿ tîⁿ sin', 'do things in such a way as not to involve yourself.', '560'): 'lṳ́ cò̤ sṳ̄ màiⁿ tîⁿ sin',
    ('tang-cì pí hē-cì muéⁿ jît thài-îang só̤ tîⁿ kâi tō ke kíam ho̤h cōi', 'the path which the sun daily follows is of very different length in winter from what it is in summer.', '560'): 'tang-cì pí hē-cì múeⁿ jît thài-îang só̤ tîⁿ kâi tō ke kíam ho̤h cōi',
    ('i kâi cṳ līam khṳ̀ kût-tîah kût-tîah', 'he recites his lesson very glibly, without any hesitation.', '562'): 'i kâi cṳ līam khṳ̀ kût-kût tîah-tîah, li-li līam',
    ('sĭang sĭm sĭ cièⁿ-seⁿ tīaⁿ', 'this is the utmost.', '562'): 'sĭang sĭm sĭ cìeⁿ-seⁿ tīaⁿ',
    ('câp-it tiám lío', "it is already eleven o'clock.", '563'): 'câp-it tíam lío',
    ('cêh nâng tiak cêk peh ē, cek̂ nâng tiak sì-câp ē', 'one was beaten a hundred, and the other forty blows.', '563'): 'cêh nâng tiak cêk peh ē, cêk nâng tiak sì-câp ē',
    ('thiaⁿ-kìⁿ mn̂g tīak-tīak-kìe', 'heard a knocking at the door.', '563'): 'thiaⁿ-kìⁿ mn̂g tiak-tiak-kìe',
    ('tiám-sim', 'luncheon.', '563'): 'tíam-sim',
    ('àiⁿ hiah cîah tiám-sim', 'will stop and take lunch.', '563'): 'àiⁿ hiah cîah tíam-sim',
    ('cí kâi îap-tîap ēng kú huang-hāi, tîeh lêng-ūaⁿ ūaⁿ kâi îap-tîap', 'these hinges having been used a long time are worn out, and must be replaced by new ones.', '564'): 'cí kâi iap-tîap ēng kú huang-hāi, tîeh lêng-ūaⁿ ūaⁿ kâi îap-tîap',
    ('chin-chīeⁿ ngâu-hṳ̂ thut-chut kim kau-tìeⁿ', 'like a grampus escaping a golden hook.', '565'): 'chin-chĭeⁿ ngâu-hṳ̂ thut-chut kim kau-tìeⁿ',
    ('kīaⁿ lío tien-a-tien', 'went stumbling along.', '566'): 'kîaⁿ lío tien-a-tien',
    ('màiⁿ khak tieh ì', 'do not brood over it too persistently.', '566'): 'màiⁿ khah tieh ì',
    ('saⁿ câp lâk tîeh, cáu ûi sĭang tieh', 'among all the moves in chess, to move forward your men is the best.', '566'): 'saⁿ câp lâk tieh, cáu ûi sĭang tieh',
    ('úa tō̤ lō tèng ngŏ̤ tîeh i', 'I came across him on the way.', '566'): 'úa tŏ̤ lō tèng ngŏ̤ tîeh i',
    ('tîeh khìang ke hùe cìaⁿ tĭen ău', 'those who would venture to bring up the rear must be powerful in arms.', '567'): 'tîeh khìang ke hùe cìaⁿ káⁿ tĭen ău',
    ('tĭen-húa îap-îap-sih', 'it lightens.', '567'): 'tĭen-húe îap-îap-sih',
    ('chùang-jîp i kâi tīn-mn̂g', 'press through the opening in the ranks.', '569'): 'chùang-jîp i kâi tīn-m̂ng',
    ('hía in cêk tīn cêk tīn cêk tīn lí-kẃn khí lâi', 'the smoke keeps rising up in puffs.', '569'): 'hía in cêk tīn cêk tīn lí-kẃn khí lâi',
    ('i chen̄g kâi tio-chṳ́ bé-kùa', 'he wore a riding jacket of sable.', '569'): 'i chēng kâi tio-chṳ́ bé-kùa',
    ('ngṳn̂-tĭaⁿ ēng jîh cōi tìo?', 'How many strings of paper ingots will be required?', '569'): 'ngṳ̂n-tĭaⁿ ēng jîeh cōi tìo ?',
    ('tìo tùi-lîin', 'hang up scrolls.', '569'): 'tìo tùi-lîn',
    ('tăi-sì sĭ chit jît sêng hôk cū kui-tìo', 'generally, the funeral rites are performed after the mourning garments have been worn seven days.', '569'): 'tăi-sì sĭ chit jît sêng hôk cū khui-tìo',
    ('sie ceⁿ boí, sie ceⁿ bōi', 'rivals in trade.', '57'): 'ceⁿ bói, sie ceⁿ bōi',
    ("sie ceⁿ sie ji'́ng", 'disputing in loud tones.', '57'): 'sie ceⁿ, sie jíang',
    ('cía li khah tōi tîo, hía li khah sòi tîo', 'this is too thick and that too slender.', '570'): 'cía li khah tōa tîo, hía li khah sòi tîo',
    ('pa pat tit', 'greatly and vainly desire.', '571'): 'pa put tit',
    ('khṳ̀ kuí tńg', 'went several times.', '573'): 'khṳ̀ kúi tńg',
    ('tek teǹg', 'proper; right.', '573'): 'tek tǹg',
    ('cí tîo lō m̄ tn̆g nâng', 'on this road you are not cut off from mankind, in that one you are isolated both from travellers and dwellings.', '574'): 'cí tîo lō m̄ tn̆g nâng, hṳ́ tîo lō tn̆g nâng in',
    ('cía sī kú-tn̂g kâi kòi-cheh', 'this is a far reaching scheme.', '574'): 'cía sĭ kú-tn̂g kâi kòi-cheh',
    ('hía thóiⁿ-tîeh tn̂gn tn̆g', 'that is heart-rending.', '574'): 'hía thóiⁿ-tîeh tn̂g tn̆g',
    ('i apt cŏ̤ kùe khîm tn̂g kâi nâng', 'he is one who has sat on the bench, has been a district magistrate.', '574'): 'i pat cŏ̤ kùe khîm tn̂g kâi nâng',
    ('i tn̂g-tn̂g lâ ún cí-kò̤', 'he keeps coming here to our house.', '574'): 'i tn̂g-tn̂g lâi ún cí-kò̤',
    ('m̄ cai sĭ ēng kùe tn̂g cìaⁿ hó̤ paǹg a sĭ míen kùe tn̂g', 'do not know whether he must go through the form of a trial before being set at liberty.', '574'): 'm̄ cai sĭ ēng kùe tn̂g cìaⁿ hó̤ pàng a sĭ míen kùe tn̂g',
    ('nńg-tó', 'the sides of the belly.', '575'): 'ńng-tó',
    ('tîeh cang eng, pue sie lío, lâi ù tó', 'must get a brick and heat it, and put it to his bowels to warm them.', '575'): 'tîeh cang cng, pue sie lío, lâi ù tó',
    ('tŏ-pîaⁿ', 'a trencher.', '576'): 'tŏ-pûaⁿ',
    ('cí cêk tòa kâi tī-nhg ngía căi', 'the country round here is very picturesque.', '577'): 'cí cêk tòa kâi tī-hng ngía căi',
    ('mih sṳ̄ tîeh ū kâi cak-tō', 'in all things there must be certain fixed limits.', '577'): 'mih sṳ̄ tîeh ŭ kâi cak-tō',
    ('seⁿ lâi tōa īeⁿ tōa sìeⁿ', 'tōa sin tōa hu; large framed; big and brawny.', '577'): 'seⁿ lâi tōa īeⁿ tōa sìeⁿ, tōa sin tōa hu',
    ('sái tōa cîⁿ', 'spend large sums.', '577'): 'sái tōa cìⁿ',
    ('tōa châi-chêng, tōa pún-mía', 'great intellectual and great executive ability.', '577'): 'tōa châi-chêng, tōa pún-nía',
    ('kúe taⁿ, cíu toaⁿ', 'an order for cakes and for wine.', '578'): 'kúe toaⁿ, cíu toaⁿ',
    ('toaⁿ piⁿ kheh o̤h chìe', 'it is hard to sing with out accompaniment.', '578'): 'toaⁿ piⁿ khek o̤h chìe',
    ('gûeh-hîⁿ sĭ i tôaⁿ lâi ío hó̤', 'he plays the guitar best.', '579'): 'gûeh-hiⁿ sĭ i tôaⁿ lâi ío hó̤',
    ('chong thiⁿ lâh cêk', 'an enormous candle used in an illumination in the open air.', '58'): 'chong thiⁿ lâh cek',
    ('cho̤ cêk', 'a suet candle.', '58'): 'cho̤ cek',
    ('cúi cêk', 'a cat-tail rush.', '58'): 'cúi cek',
    ('tâng cek, siah cek, pêh-thih cêk', 'a brass, pewter, or tin cylinder, holding oil and a wick for burning it.', '58'): 'tâng cek, siah cek, pêh-thih cek',
    ('íe cêk', 'make candles.', '58'): 'íe cek',
    ('cîhe mn̂g tŏiⁿ', 'stone threshold.', '580'): 'cîeh mn̂g tŏiⁿ',
    ('hŭo tŏiⁿ', 'give information to tenants of a change of landlords.', '580'): 'hŭe tŏiⁿ',
    ('i kâi mīn-tîeⁿ ngó-ngâk sì-tôk lóng-cóng bô̤ kô̤ hó̤ hîam', 'his features are all faultless.', '582'): 'i kâi mīn-tîeⁿ ngó-ngâk sì-tôk lóng-cóng bô̤ kò̤ hó̤ hîam',
    ('i sĭ toaⁿ-toaⁿ bōi jît-tôk a sī ŭ bōi thò̤-hùe?', 'Does he sell what he daily buys or does he take in and sell on commission?', '582'): 'i sĭ toaⁿ-toaⁿ bōi jît-tôk a sĭ ŭ bōi thò̤-hùe ?',
    ('kuaⁿ phoi tàⁿ "bô̤ îong tôk chíaⁿ"', 'the magistrate\'s decision was this "No appeals which are an abuse of privilege will be allowed".', '582'): 'kuaⁿ phoi tàⁿ “bô̤ îong tôk chíaⁿ”',
    ('i cŏ̤ to m̄ tiām cŏ̤, kha tŏng chíu hìⁿ', 'when he sits down he never sits still, but keeps flopping his limps about.', '583'): 'i cŏ̤ to m̄ tīam cŏ̤, kha tŏng chíu hìⁿ',
    ('i kîaⁿ lió ki piⁿ tŏng-tŏng-hìⁿ', 'his queue flops about as he walks.', '583'): 'i kîaⁿ lío ki piⁿ tŏng-tŏng-hìⁿ',
    ('ieh khṳ̀ kòi lío', 'he has fallen into the trap.', '583'): 'i tòng kòi lío',
    ('níng khun tŏng kúi ūi?', 'How many are there of you brothers?', '583'): 'nín khun tŏng kúi ūi ?',
    ('toaⁿ-toaⁿ thóiⁿ-kìⁿ tek-búe tong-tong-hìⁿ', 'saw nothing but the tops of the bamboos swaying to and fro.', '583'): 'toaⁿ-toaⁿ thóiⁿ-kìⁿ tek-búe tŏng-tŏng-hìⁿ',
    ('ūe tàng lâi tòng khéng', 'what has been said meets the exigency; spoke to the purpose or point.', '583'): 'ūe tàⁿ lâi tòng khéng',
    ('liêk căi, tîeh lâi tó̤ siap-sî', 'very weary, and must lie down a few moments.', '584'): 'hêk căi, tîeh lâi tó̤ siap-sî',
    ('nâng pí mûeh sī kùi tŏng', 'people are to be regarded rather than things.', '584'): 'nâng pí mûeh sĭ kùi tŏng',
    ('tîeh lâi tú cìaⁿ bo̤ĭ tó̤', "must brace it up then it won't fall.", '584'): 'tîeh lâi tú cìaⁿ bŏi tó̤',
    ('sieh nâng tò̤ chin-chĭeⁿ hēng nâng hìeⁿ-seⁿ', 'loves people and appears as it he hated them.', '585'): 'sieh nâng tò̤ chin-chĭeⁿ hĕng nâng hìeⁿ-seⁿ',
    ('tô̤ jîp chim suanⁿ nâ lăi', 'fled into the recesses of the mountains.', '585'): 'tô̤ jîp chim suaⁿ nâ lăi',
    ('tô̤-síam put kîp, khṳ̄t i sīa tîeh', 'did not dodge quickly enough, and was hit by his arrow.', '585'): 'tô̤-síam put kîp, khṳt i sīa tîeh',
    ('bô̤ nâng bŏ̤', 'there is nobody there.', '586'): 'bô̤ nâng tŏ̤',
    ('hīⁿ tô̤', 'the lobe of the ear.', '586'): 'hĭⁿ tô̤',
    ('âk-kìaⁿ tō̤', 'a spectacle-case.', '586'): 'mâk-kìaⁿ tŏ̤',
    ('chíeⁿ-tô̤h nâng kâi mûeh', "seize and carry off people's goods.", '587'): 'chíeⁿ-tôh nâng kâi mûeh',
    ('hó̤ kâi khṳ̂ nâng soiⁿ tô̤h khṳ̀', 'the good ones were all taken previously.', '587'): 'hó̤ kâi khṳt nâng soiⁿ tô̤h khṳ̀',
    ('i to̤h i m̄ kùe', 'he could not snatch it from her.', '587'): 'i tô̤h i m̄ kùe',
    ('tiêh phuah kàu nĕ tô̤h-tô̤h', 'on hearing it, his wrath waxed hot.', '587'): 'cē thiaⁿ tîeh húe cū tô̤h',
    ('to̤h kīⁿ', 'a stand with drawers.', '587'): 'to̤h kūiⁿ',
    ('tò̤ tò̤ cêk tu', 'pour them together in a pile.', '587'): 'tò̤ cò̤ cêk tu',
    ('tô̤h kâi bó̤ jît', 'select a lucky day.', '587'): 'tô̤h kâi hó̤ jît',
    ('tú tîeh a tú m̄ tiêh?', 'Does it abut upon it or not?', '588'): 'tú tîeh a tú m̄ tîeh',
    ('cîah tû', 'kîam sng tû; a food safe.', '589'): 'cîah tû ； kîam sng tû',
    ('ngṳ̂n sŭ lâk-poih tŭe a sĭ chit tŭe?', 'Are the dollars current here reckoned at six mace right candareens, or at seven mace?', '589'): 'ngṳ̂n sĭ lâk-poih tŭe a sĭ chit tŭe？',
    ('cêk ciah cío', 'a bird.', '59'): 'cêk ciu kîe; cêk tún kîe; cêk tîo kîe',
    ('cêk tùi huń-cío', 'a pair of pigeons.', '590'): 'cêk tùi hún-cío',
    ('hàm i tùu úa kò̤ lâi', 'tell him to come along by my house.', '590'): 'hàm i tùi úa kò̤ lâi',
    ('i sĭ tng mīn tùi úi tàⁿ kùe kâi', 'it is what he told me to my face.', '590'): 'i sĭ tng mīn tùi úa tàⁿ kùe kâi',
    ('nŏ̤ nâng sī tùi-thâu kâi wn-ke', 'the two are rivals of each other.', '590'): 'nŏ̤ nâng sĭ tùi-thâu kâi wn-ke',
    ('hṳ́ kâi kíaⁿ-tĭ sĭ hùi-tŭi kâi kíaⁿ-tī', 'that son of hers is a poor stick.', '591'): 'hṳ́ kâi kíaⁿ-tĭ sĭ hùi-tŭi kâi kíaⁿ-tĭ',
    ('i kâi chíu khṳ̂ tùi hám tîeh', 'her hand was hit by the descending pestle.', '591'): 'i kâi chíu khṳt tùi hám tîeh',
    ('cûn-thâu-so̤h khṳt huang-éng tùng tn̆g khṳ̀', 'the rope by which the boat is made fast, has been broken by the storm.', '592'): 'cûn-thâu-so̤h khṳt huang-éng tùn tn̆g khṳ̀',
    ('hìeⁿ pôiⁿ kâi tùi cē ceng, cìeⁿ pôiⁿ kâi tī tū ŏi tùn', 'when the pounder comes down on the other side, the ground on this side trembles.', '592'): 'hìeⁿ pôiⁿ kâi tùi cē ceng, cìeⁿ pôiⁿ kâi tī cū ŏi tùn',
    ('sía “ cài pài” cū hó̤, mín sía “tŭn sía pài,”', 'if you write “I present my respects” (on the card), you need not write “I respectfully bow the head.”', '592'): 'sía “cài pài” cū hó̤, mín sía “tŭn síu pài”',
    ('chŵn tṳ', 'a whole hog.', '593'): 'thâi tṳ',
    ('tṳ khah-kih', "pig's feet.", '593'): 'tṳ kha-kih',
    ('tṳ tiam', "a butcher's block.", '593'): 'tṳ to̤',
    ('tṳ tîeh cô̤', 'the pig is sick.', '593'): 'tṳ tîeh co̤',
    ('tṳ tô̤', "butcher's shop.", '593'): 'tṳ-tô',
    ('gê tṳ̄, tek tṳ̄, o tṳ̄, ngṳ̂ tṳ̄', 'chopsticks of ivory, of bamboo, of ebony, or of silver.', '594'): 'gê tṳ̄, tek tṳ̄, o tṳ̄, ngṳ̂n tṳ̄',
    ('i kâi sim-sût puttwn', 'his notions are incorrect.', '594'): 'i kâi sim-sût put twn',
    ('isĭ twn-cìaⁿ kâi nâng', 'he is an upright man.', '594'): 'ĭsi twn-cìaⁿ kâi nâng',
    ('sieⁿ ngûⁿ kâi tṳ̄', 'chopsticks plated with silver.', '594'): 'sieⁿ ngṳ̂n kâi tṳ̄',
    ('that khah lang', 'the sieve is too coars.', '595'): 'thai khah lang',
    ('ṳ́ ŭ kìⁿ kùe a-thài mē?', 'Have you seen Madame?', '595'): 'lṳ́ ŭ kìⁿ kùe a-thài mē ?',
    ('htak kîu', 'play foot-ball.', '596'): 'thak kîu',
    ('i nŏ̤ nâng thâk kha lío khuang-phìen i', 'the one gave the other a hint by a little kick and both combined to befool him.', '596'): 'i nŏ̤ nâng thak kha lío khuang-phìen i',
    ('kẃn-thăi i cò̤ nâng-khek', 'treat him as if he were a guest.', '596'): 'kẃn-thăi i cò̤ nâng-kheh',
    ('sío-jîn hṳ̀ kio-ngău kâi thāi', 'the hauteur of a plebeian; the air of a parvenu.', '596'): 'sío-jîn hùe kio-ngău kâi thāi',
    ('thài kong, thài phûa', 'lău thài îa, thài má; are appelations of the parents of men of repute.', '596'): 'thài kong; thài phûa; lău thài îa; thài má',
    ('thâ', 'To carry between two or more persons on a pole; to put forward.', '596'): 'thâi',
    ('thăi khah hú, cò̤ i khṳ̀', 'had too long to wait, and went off.', '596'): 'thăi khah kú, cò̤ i khṳ̀',
    ('nâng m̄ hó̤ khah tham, khak tham cū tîeh gō sṳ̄', 'one should not be too inordinately desirous of anything, for so doing thwarts its object.', '597'): 'nâng m̄-hó̤ khah tham, khah tham cū tîeh gō sṳ̄',
    ('tham-khû i ŏi sie thâi', 'calculated upon their fighting.', '597'): 'tham-thû i ŏi sie thâi',
    ('thâk sòin siaⁿ', 'read in a low tone.', '597'): 'thâk sòi siaⁿ',
    ('tám khak', 'to tie a knot.', '597'): 'thám khak',
    ('cêk cūn thâm lâi kàu cū ĭng-kùo-khṳ̀', 'when the death-rattle comes one dies at once.', '598'): 'cêk cūn thâm lâi kàu cū tn̆g-kùe-khṳ̀',
    ('cía sĭ ngŏ̤ tîeh thâm un sṳ̀ kâi', 'this is having a vast favor conferred on me.', '598'): 'cía sĭ ngŏ̤ tîeh thâm ṳn sṳ̀ kâi',
    ('thām kàu cêk sin cĕng-cĕng thô-kâu-mûeⁿ', 'got mired so deeply that he was wholly covered with mud.', '598'): 'thām kàu cêk sin cĕng-cĕng thô-kau-mûeⁿ',
    ('thām lo̤h khṳ̀ lok-cē-kìe', 'splashed as he sank in the mud.', '598'): 'thām lô̤h khṳ̀ lok-cē-kìe',
    ('buêh tháng', 'bûeh àng; the leg of a stocking.', '599'): 'bûeh tháng; bûeh àng',
    ('cîⁿ?', 'What is the amount to be paid by each as his share?', '599'): 'kâi nâng thang khí lâi ēng jîeh cōi cîⁿ ?',
    ('nêk ŭ thang khṳt nâng cîah, kut bô̤ thang khṳ̂t nâng khòi', 'have meat that I can let people eat, but no bones to let them gnaw; will stand some imposition, but not an unlimited amount of it.', '599'): 'nêk ŭ thang khṳt nâng cîah, kut bô̤ thang khṳt nâng khòi',
    ('sĭu i kâi ĭu lío cū tháng-ciàm i', 'takes his bribe and helps him therefor.', '599'): 'sĭu i kâi ĭu lío cū tháng-cìam i',
    ('lṳ́ thóiⁿ sî-ceng kṳ́i tíam', 'look at the clock and see what time it is.', '60'): 'lṳ́ thóiⁿ sî-ceng kúi tíam',
    ('i kâi suū thàng căi', 'his affairs are thoroughly settles.', '600'): 'i kâi sṳ̄ thàng căi',
    ('i thóiⁿ thàng tī-keh', 'he can see through the earth.', '600'): 'i thóiⁿ thàng tĭ-keh',
    ('thek-tháng', 'as he sat there one could at once see that he was some extraordinary person.', '600'): 'i cŏ̤ pàng ko̤ thóiⁿ tîeh lêng-gūa thek-tháng',
    ('gūa mīn thóiⁿ-kìⁿ li thâng-thâng hûang-hûang, khî-sît sĭang siò-khì', 'has a very imposing appearance but is really petty.', '601'): 'gūa mīn thóiⁿ-kìⁿ li thâng-thâng hûang-hûang, khî-sît sĭang sìo-khì',
    ('tṳ̂ sî, thàng kàu lâk peh', 'subtracting all losses, there remained a gain of six hundred.', '601'): 'tṳ̂ sît, thàng kàu lâk peh',
    ('cí kâi suaⁿ thap jîp ho̤h chi khṳ̀', 'this hill is gullied rather deeply.', '602'): 'cí kâi suaⁿ thap jîp ho̤h chim khṳ̀',
    ('khṳt i thâu ôiⁿ khùn-kíaⁿ', "let her steal a moment's leisure.", '602'): 'khṳt i thau ôiⁿ khùn-kíaⁿ',
    ('mûeh-kīaⁿ khṳt i thau-tău jîeh cōi', 'a great number of articles have been purloined by her.', '602'): 'mûeh-kĭaⁿ khṳt i tau-tău jîeh cōi',
    ('níoⁿ-chṳ́ thàu jît-kùn káⁿ chut lâi', 'the rats venture out even in the daytime.', '602'): 'níoⁿ-chṳ́ thàu jît-kùa káⁿ chut lâi',
    ('thàu cú thàu àm cò̤', 'does it early and late.', '602'): 'thàu cá thàu àm cò̤',
    ('cí kò̤ gêk ío thàu-lĭang, hṳ́ kò̤ gêk bô̤ hìoⁿ thàu-lĭang', 'this piece of jade is translucent, while that one is not very clear.', '603'): 'cí kò̤ gêk ío thàu-lĭang, hṳ́ kò̤ gêk bô̤ hìeⁿ thàu-lĭang',
    ('i bô̤ sĭoⁿ thâu', 'there is no other way for him to do; he sees no way out of it.', '603'): 'i bô̤ sĭeⁿ thâu',
    ('mâiⁿ kheh thàu', 'do not put yourself out on my account.', '603'): 'màiⁿ kheh thàu',
    ('khṳ̂ châk pak kàu teh-theh khṳ̀', 'stripped naked by robbers.', '604'): 'khṳt châk pak kàu theh-theh khṳ̀',
    ('ā-sŭ ŭ huang cûn cū mín theⁿ', 'should there be wind we need not pole the boat.', '604'): 'ā-sĭ ŭ huang cûn cū mín theⁿ',
    ('i kâi sî théng m̄ khui', 'it cannot spread its wings.', '605'): 'i kâi sît théng m̄ khui',
    ('i sît-că hó̤ im-thek', 'he is really philanthropic.', '605'): 'i sît-căi hó̤ im-thek',
    ('caù-cai chîo-thêng', 'inform the government or the Emperor.', '606'): 'càu-cai chîo-thêng',
    ('cía khí lô̤h khṳ̀ sĭ tōa kang thēng kâi', 'this taken altogether is a big job.', '606'): 'cía khí lô̤h khṳ̀ sĭ tōa kang thêng kâi',
    ('cúi kàu cí kò̤ cū thêng lâi', 'the current sets backward from this point.', '606'): 'cúi kàu cí kò̤ cū thêng lâu',
    ('màiⁿ theǹg thiaⁿ nâng kâi ūe', 'do not indiscriminately listen to people.', '606'): 'màiⁿ thèng thiaⁿ nâng kâi ūe',
    ('thèng khî cṳ̆-jîen, maìⁿ míen-kíang i', 'let it take its natural course; wait till it comes about of itself; do not force it at all.', '606'): 'thèng khî cṳ̆-jîen, màiⁿ míen-kíang i',
    ('khô̤ kàu nĕ thi-thi', 'simmer it till it is very gummy.', '607'): 'khô̤h kàu nĕ thi-thi',
    ('chwn tn̂g thĭ', 'chwn chîang thĭ; a fistula in ano.', '608'): 'chwn tn̂g thĭ ; chwn chîang thĭ',
    ('hoó̤ thiⁿ', 'fine weather.', '608'): 'hó̤ thiⁿ',
    ('kau toŏ thî-thîo-kuaⁿ kò̤', 'handed over to the proctor.', '608'): 'kau tŏ̤ thî-thîo-kuaⁿ kò̤',
    ('m̄ cai thî-hûang cū khíong-ùi gō suū', 'if you do not take care you will very likely quash the project.', '608'): 'm̄ cai thî-hûang cū khíong-ùi gō sṳ̄',
    ('thiⁿ thī nâng kìe-cò̤ sam châi', 'heaven earth and man are called the three great powers.', '608'): 'thiⁿ tī nâng kìe-cò̤ sam châi',
    ('thì ho̤h cōi têng lâi', 'have taken off ever so many layers.', '608'): 'thì ho̤h cōi têng chut lâi',
    ('chng cam lío, sùaⁿ thám khah cìaⁿ hó̤ thīⁿ', 'when the needle is threaded, tie a knot in the thread and then sew.', '609'): 'chng cam lío, sùaⁿ thám khak cìaⁿ hó̤ thīⁿ',
    ('cì thiⁿ', 'cí tī; offer sacrifice to the heavens and the earth.', '609'): 'cì thiⁿ, cì tī',
    ('i ío thiaⁿ̀ nâng tàⁿ', 'he is more obedient.', '609'): 'i ío thiaⁿ nâng tàⁿ',
    ('lîe tó̤ cē, thīⁿ khí lâi cìaⁿ ka', 'trim it off a little shorter, then when it is sewn it will be just the right length.', '609'): 'lîe tó̤ cē, thīⁿ khí lâi cìaⁿ kah',
    ('tng-thiⁿtáu-cok', 'pray under the open sky.', '609'): 'tng-thíⁿtau-cok',
    ('îeh ā-sĭ cîah m̄ tùi cū àiⁿ jú-keǹ thiⁿ pēⁿ', 'if one takes medicine that is unsuitable he becomes the more ill.', '609'): 'îeh ā-sĭ cîah m̄ tùi cū àiⁿ jú-kèng thiⁿ pēⁿ',
    ('seⁿ lâi ceng-sîn câi', 'naturally very vigorous.', '61'): 'seⁿ lâi ceng-sîn căi',
    ('i jiáng tó thìaⁿ', 'he cries because he has a pain in his stomach.', '610'): 'i jíang tó thìaⁿ',
    ('thiah chù téng', 'thiah chù hĭa; tear up a roof.', '610'): 'thiah chù téng; thiah chù hĭa',
    ('jîeh thìaⁿ', 'feverish pain.', '610'): 'jîet thìaⁿ',
    ('i kâi sṳ̄ cò̤ lâi thó̤-thiapcăi', 'his affairs are very thoroughly settled.', '611'): 'i kâi sṳ̄ cò̤ lâi thó̤-thiap căi',
    ('khîeh thîap', 'received written invitations.', '611'): 'khîeh thiap',
    ('thian teng', "to have an increase in one's family.", '611'): 'thiam teng',
    ('thiap mīn, thiam chiam', 'the outside of the note and the address thereon.', '611'): 'thiap mīn, thiap chiam',
    ('thó̤i-thiap; thí-thiap', "to take up another's cause; to act in behalf of another; to patronize; to accommodate another.", '611'): 'thói-thiap; thí-thiap',
    ('nâng tàⁿ i sĭ tit tîeh thien-cṳ cìaⁿ ŏi', 'people say that he has received books from celestial regions and is therefore thus gifted.', '612'): 'nâng tàⁿ i sĭ tit tîeh thien-cṳ cìaⁿ cìeⁿ ŏi',
    ('cū sĭthih cîeh sim-tn̂g thóiⁿ tîeh ĭa put jím', "though one's feelings were hard as rock, one could not endure the sight.", '613'): 'cū sĭ thih cîeh sim-tn̂g thóiⁿ tîeh īa put jím',
    ('cûn iô-ît căi, cn̂g kâi tó̤ thìo', 'the boat is very uneasy, and is all the time pitching and rolling.', '614'): 'cûn io-ît căi, cn̂g kâi tó̤ thìo',
    ('i kâi châi-chêng sît-cāi thìo khûn', 'his abilities are above the common run.', '614'): 'i kâi châi-chêng sît-căi thìo khûn',
    ('tô̤ kâi sì cū thìo kùu khṳ̀', 'rallied his force and jumped across.', '614'): 'tô̤ kâi sì cū thìo kùe khṳ̀',
    ('cía cĭ cò̤-nî thiu-thâu?', 'What proportion of this is to be taken as fees?', '615'): 'cía sĭ cò̤-nî thiu-thâu',
    ('gû-nêk-thng', 'beef broth.', '615'): 'chwn thng',
    ('i sĭ m̄ hôkcúithó', 'the climate does not agree with him.', '616'): 'i sĭ m̄ hôk cúi thó',
    ('thǹng būe sêk', 'they are not yet scalded through.', '616'): 'thǹg būe sêk',
    ('thôu ûi', 'an enclosing wall made of earth.', '617'): 'thô ûi',
    ('chut sin lò thói', 'chiah sin lò thói; stark naked.', '618'): 'chut sin lò thói ; chiah sin lò thói',
    ('i thóiⁿ i, ithóiⁿ i', 'looking at each other.', '618'): 'i thóiⁿ i, íthoiⁿ i',
    ('thóiⁿ m̄ chit', 'cannot perceive it.', '618'): 'thóiⁿ m̄ chut',
    ('hṳ́ lăihùaⁿ nâng cū sĭ cí kâi sĭang tit thóng', 'of all those in there this is the one that is most beloved.', '619'): 'hṳ́ làihuaⁿ nâng cū sĭ cí kâi sĭang tit thóng',
    ('múaⁿ-tī kò̤ cǹng kàu kio ngĭ-thóng-po hìeⁿ-seⁿ', 'graves are everywhere as thick as in a public cemetery.', '619'): 'múaⁿ-tī kò̤ cǹg kàu kio ngĭ-thóng-po hìeⁿ-seⁿ',
    ('tîeh ŭ ke cêk nâg nā hṳ́ ĕ thok khí', 'there should be another person down below pushing it upward.', '619'): 'tîeh ŭ ke cêk nâng nā hṳ́ ĕ thok khí',
    ('i kâi thông-jîn en̂g kâi bū', 'the pupils of his eyes have a cloudy look all over them.', '620'): 'i kâi thông-jîn cn̂g kâi bū',
    ('lṳ́ thóiⁿ thó̤-tǹg a m̄ thó̤-tǹng?', 'Do you consider it all securely settled or not?', '620'): 'lṳ́ thóiⁿ thó̤-tǹg a m̄ thó̤-tǹg',
    ('i to bŏi tàⁿ ūa lṳ́ cò̤ hó̤ tho̤h i tàⁿ ūe', 'as he si no talker, why do you entrust the negotiation to him.', '621'): 'i to bŏi tàⁿ ūe lṳ́ cò̤ hó̤ tho̤h i tàⁿ ūe',
    ('tho̤h-cío', 'the ostrich, or cassowary of the Indian Archipelago.', '621'): 'thô̤h-cío',
    ('thô̤-ki lío-ki sĭ ēng lâi phek sîa phek kúi', 'peach and willow branches are used for driving out noxious influences and demons.', '621'): 'thô̤-ki líu-ki sĭ ēng lâi phek sîa phek kúi',
    ('hū-thû', 'inapt, unready, blundering.', '622'): 'hû-thû',
    ('kàu cē cṳ̀-bwn̆n cū lâng thû', 'when it has widely ramified it will be difficult to extirpate.', '622'): 'kàu cē cṳ̀-bw̆n cū lâng thû',
    ('kâi kíaⁿ hó̤ thû cò̤ kuaⁿ, kâi kíaⁿ bó̤ thû hwt châi', "may reckon upon one's son's being an official, and upon the other one's becoming rich.", '622'): 'kâi kíaⁿ hó̤ thû cò̤ kuaⁿ, kâi kíaⁿ hó̤ thû hwt châi',
    ('thuaⁿ kâi cúi li kĭa, īu sà-sà, cĕng-cĕng cîeh, kù-chṳ́ kùe thuaⁿ kâi sî-liāu nâng-nâng kiaⁿ', 'the rapids are steep, and full of projecting rocks, so that in passing them every one is in dread.', '622'): 'thuaⁿ kâi cúi li kĭa, īu sà-sà, cĕng-cĕng cîeh, kù-chṳ́ kùe thuaⁿ kâi sî-hāu nâng-nâng kiaⁿ',
    ('úa thieⁿ thui tŏ̤ chîeⁿ kò̤', 'lean a ladder against a wall.', '623'): 'úa tieⁿ thui tŏ̤ chîeⁿ kò̤',
    ('cìeⁿ-seⁿ būe lă khṳ̂t i thun khṳ̀', 'there is not enough to satisfy his rapacity.', '624'): 'cìeⁿ-seⁿ būe lă khṳt i thun khṳ̀',
    ('thūn kàu i múaⁿ-múaⁿ khí lâi', 'fill it in quite to the top.', '624'): 'thūn kàu i múaⁿ-múaⁿ khí kâi',
    ('u huang, hŵn hŏ', 'call for wind and rain as jugglers do.', '625'): 'u huang, hẁn hŏ',
    ('cong jît to sí hwn-û hì-lâk', 'amusements and pleasure throughout the day.', '626'): 'cong jît to sĭ hwn-û hì-lâk',
    ('i seⁿ lâi kâi khì ú put pûam', 'his talents and his countenance are uncommon.', '626'): 'i seⁿ lâi kâi khì ú put hûam',
    ('mn̄g úaⁿl chíaⁿ uaⁿ', 'to salute.', '627'): 'm̄ng úaⁿl chíaⁿ uaⁿ',
    ('phì-ju cò̤ céⁿ tói ua', 'like a frog that lives in a well.', '627'): 'phì-jŭ cò̤ céⁿ tói ua',
    ('uaⁿ-húang pù-kùi', 'enjoy wealth and honor.', '627'): 'uaⁿ-híang pù-kùi',
    ('úa sĭ bô̤ ta ûa khṳ̀ it kò̤', 'I had no other way but to go where he was.', '627'): 'úa sĭ bô̤ ta ûa khṳ̀ i kò̤',
    ('i chông-côiⁿ ā sĭ khéng o̤h hó̤ le, kim-jît uaⁿ ŏi cìeⁿ-seⁿ?', 'Had he formerly learned to do well, how could he be as he now is?', '628'): 'i chông-côiⁿ ā sĭ khéng ô̤h hó̤ le, kim-jît uaⁿ ŏi cìeⁿ-seⁿ ?',
    ('i thóiⁿ tîeh m̄-hó̤, aìⁿ ūaⁿ tò̤-tńg', 'he thinks them of inferior quality, and wants to have them taken back.', '628'): 'i thóiⁿ tîeh m̄-hó̤, àiⁿ ūaⁿ tò̤-tńg',
    ('ūaⁿ kàu múaⁿ-tī-kò̤ bô̤ cúi', 'so dry that there is no water anywhere.', '628'): 'ŭaⁿ kàu múaⁿ-tī-kò̤ bô̤ cúi',
    ('bōi ûah', 'it will not live.', '629'): 'bŏi ûah',
    ('cêk tó húe uak-uak jîeh', 'in a perfect rage.', '629'): 'cêk tó húe uak-uak jîet',
    ('húe uak-uak jîeh', 'the fire is blazing how.', '629'): 'húe uak-uak jîet',
    ('m̄ cai i sĭ sí a sí ûah', 'do not know whether he is dead of a live.', '629'): 'm̄ cai i sĭ sí a sĭ ûah',
    ('ûah hok bô̤ kiang', 'obtain endless bliss.', '629'): 'ûak hok bô̤ kiang',
    ('péng cèng', 'cip cèng; to hold authority.', '63'): 'péng cèng cip cèng',
    ('ngŏ̤ tîeh at hùe cū ŭang m̄ kùe chíu', 'if he falls in with those who understand such matters, he cannot deceive them by that dodge.', '630'): 'ngŏ̤ tîeh pat hùe cū ŭang m̄ kùe chíu',
    ('tōa ûang', 'the eldest and next to the eldest of the princes.', '630'): 'tōa ûang, jī ûang',
    ('úang chîang', 'úang jît; constantly; usually; formerly.', '630'): 'úang chîang; úang jît',
    ('kok ûang', 'ûang ke; the kind.', '630'): 'kok ûang; ûang ke',
    ('chīe cē khah ùe cū khíong-ùi tìam ŭ nĭoⁿ-hóⁿ', 'if the trees become too thick there is danger that tigers will conceal themselves therein.', '631'): 'chīu cē khah ùe cū khíong-ùi tìam ŭ nĭoⁿ-hóⁿ',
    ('hṳ́ kò̤ kâi chīu-lîm nĕ uè-ùe', 'the thickets there are very dense.', '631'): 'hṳ́ kò̤ kâi chīu-lîm nĕ ùe-ùe',
    ('kheh ūe', 'the Hakka tongue.', '632'): 'hwn ūe',
    ('hŏng cŏeⁿ-si kâi úi', 'receive the orders of a superior officer.', '633'): 'hŏng cĭeⁿ-si kâi úi',
    ('pbài úi-ŵn khṳ̀ chê', 'send a deputy to examine.', '633'): 'phài úi-ŵn khṳ̀ chê',
    ('cèng ūi hiaⁿ-tĭ', 'all of you brethren.', '635'): 'lîet ūi thiaⁿ úa tàⁿ',
    ('cía cĭ un-hûa kâi îeh', 'this is a sedative medicine.', '635'): 'cía sĭ un-hûa kâi îeh',
    ('i in-ūi tîeh cí kĭaⁿ cṳ̄ cū lâi', 'it was on this account that he came.', '635'): 'i in-ūi tîeh cí kĭaⁿ sṳ̄ cū lâi',
    ('lîet ūi thŵn khṳ tī-tîang?', 'To whom did his throne descend?', '635'): 'i kâi thiⁿ-ūi thŵn khṳt tī-tîang ?',
    ('ū pâng ūi a bô̤?', 'Is there a room for me (in the inn)?', '635'): 'ŭ pâng ūi a bô̤ ?',
    ('ūi', 'The stomach.', '635'): 'phêng ūi',
    ('cí cîk tîeⁿ kháu khṳ̀ pí cĭeⁿ tîeⁿ m̄ ûn-cēng', 'this class did not equal the preceding one in the examination.', '636'): 'cí cêk tîeⁿ kháu khṳ̀ pí cĭeⁿ tîeⁿ m̄ ûn-cēng',
    ('si sĭ poit ūn a sĭ lâk ūn?', 'Have the verses sixteen lines with the alternate lines rhyming, or have they twelve lines containing six rhymes?', '636'): 'si sĭ poih tīn a sĭ lâk ūn ?',
    ('chia ût m̄ tńgh', 'cannot turn the cart around.', '637'): 'chia ût m̄ tńg',
    ('thâu-kah-chat ût', 'lie with heads in opposite directions.', '637'): 'thâu-kah-chah ût',
    ('khî-ṳ̂ kâi bó̤ lâu cò̤ céng-cí', 'save what is left for seed.', '638'): 'khî-ṳ̂ kâi hó̤ lâu cò̤ céng-cí',
    ('khṳt i kù ūe û lâi kàn, i cū khì', 'when this utterance of hers reached him, he was angry.', '638'): 'khṳt i kù ūe ṳ̂ lâi kàu, i cū khì',
    ('cí kuah', 'cí âu; quench thirst.', '64'): 'cí kuah ； cí âu',
    ('tâng tìn-thâi lâi pōiⁿ cêk ùaⁿ ău, tī-hng cĭu ío uaⁿ-cĕng', 'after the general-in-chief came and put the country in order, it was more settled and peaceful.', '64'): 'tâng tìn-thâi lâi pōiⁿ cek ùaⁿ ău, tī-hng cĭu ío uaⁿ-cĕng',
    ('cì thiⁿ tī', 'worship heaven and earth. cì sĭa cek; worship the gods of land and grain.', '65'): 'cì sĭa cek',
    ('ciⁿ lî, irrelevant', 'evasive.', '66'): 'ciⁿ lî',
    ('cía khak sòi', 'this is much too small.', '68'): 'cía khah sòi',
    ('pńg cĭa', 'ngŵn cĭa; the original family seat.', '68'): 'pńg cĭa ; ngŵn cĭa',
    ('cí cîah cûn cĭu cîah chim cúi', 'this boat draws much water.', '70'): 'cí ciah cûn cĭu cîah chim cúi',
    ('thâng cîah thâng', 'tōa thâng cîah sòi thâng; animals live on animals, the larger eating the smaller.', '70'): 'thâng cîah thâng tōa thâng cîah sòi thâng',
    ('cĭam', 'Gradually; by degrees.', '72'): 'cĭam tōa',
    ('cìang mn̂g cṳ cṳ́', 'of the breed of warriors.', '73'): 'cìang m̂ng cṳ cṳ́',
    ('lăi-ciàng', 'paralysis of the optic nerve.', '73'): 'lăi-cìang',
    ('tá sèng cīang', 'victorious in the fight.', '73'): 'tá sèng cĭang',
    ('ēng i tó̤ cíeⁿ câh-mn̂g', 'employ him to guard the barrier.', '75'): 'ēng i tó̤ cíeⁿ câh-m̂ng',
    ('cih lío tab cò̤ cêk ē', 'after folding them, put them together in a pile.', '78'): 'cih lío tah cò̤ cêk ē',
    ('cíen ngî; cíen kîaⁿ; cíen pîet; cíen níu', 'parting presents.', '78'): 'cíen ngî; cíen kîaⁿ; cíen pîet; cíen lói',
    ('tŏ̤ suaⁿ tèng ngŏ̤ tîeh cīu cìen', 'met and fought on the hills.', '78'): 'tŏ̤ suaⁿ tèng ngŏ̤ tîeh cĭu cìen',
    ('úa thó̤iⁿ tîeh cin ngía', 'I consider it really beautiful.', '80'): 'úa thóiⁿ tîeh cin ngía',
    ('cit hue chaú', 'to weave flowered fabrics.', '83'): 'cit hue cháu',
    ('i ciu siì nâng cìeⁿ-seⁿ', 'he has been like that all his life.', '83'): 'i ciu sì nâng cìeⁿ-seⁿ',
    ('sĭ i lâi cīu úa, m̄ sĭ úa khṳ̀ cĭu i', 'it is for him to come to me, not for me to go to him.', '84'): 'sĭ i lâi cĭu úa, m̄ sĭ úa khṳ̀ cĭu i',
    ('thiⁿ-sî chìn, cíu tîeh un sie cē m̄ pí jûah thiⁿ-sî cò̤ chìn cíu to̤ hó̤ cîah', 'the weather being cold the wine must be heated more: it is not as it is in hot weather, when one may take his wine cold.', '84'): 'thiⁿ-sî chìn, cíu tîeh un sie cē: m̄ pí jûah thiⁿ-sî cò̤ chìn cíu to̤ hó̤ cîah',
    ('cōi kâu sǹg m̄ pat tò̤ khṳ̀', 'so many as to be countless.', '86'): 'cōi kàu sǹg m̄ pat tò̤ khṳ̀',
    ('thēng côi, cìaⁿ lâi', 'wait till you have the full complement and then come.', '86'): 'thĕng côi, cìaⁿ lâi',
    ('gû-nêk tieh khîeh-khí màiⁿ khṳt hĭa lâi cn̂g', 'the beef must be put away so that the ants will not get at it.', '86'): 'gû-nêk tîeh khîeh-khí màiⁿ khṳt hĭa lâi cn̂g',
    ('sêng có kâi nâng', 'sêng nâng kâi có; become the head of a house or tribe.', '86'): 'sêng có kâi nâng; sêng nâng kâi có',
    ('cò̤ coih', 'kùe coih; to keep holiday.', '87'): 'cò̤ coih; kùe coih',
    ('lṳ́ tó̤ cò̤ mîh sṳ̄?', 'What are you doing?', '90'): 'lṳ́ tó̤ cò̤ mih sṳ̄ ?',
    ('tîeh', 'you have decided rightly.', '93'): 'lṳ́ cú-ì lâi tîeh',
    ('cûa ŭ kâi ŏ̤i tâk, ŭ kâi bŏi', 'some serpents are poisonous and some are not.', '94'): 'cûa ŭ kâi ŏi tâk, ŭ kâi bŏi',
    ('cúa bûe', 'cúa ín; paper used as tinder.', '94'): 'cúa bûe; cúa ín',
    ('cuí thóiⁿ tîeh cûak, m̄ cheng-khih', 'the water does not appear to be clean.', '95'): 'cúi thóiⁿ tîeh cûak, m̄ cheng-khih',
    ('lêng-ūaⁿ sǹg, sǹg tîeh bŏ̤i cûah', 'reckoned it up again, and found there was no deficiency.', '95'): 'lêng-ūaⁿ sǹg, sǹg tîeh bŏi cûah',
    ('cuang chut lâi hó̤thóiⁿ', 'very prettily dressed.', '96'): 'cuang chut lâi hó̤ thóiⁿ',
    ('cuang sok khí lâi hó̤thóiⁿ', 'bind up the travelling equipments nicely.', '96'): 'cuang sok khí lâi hó̤ thóiⁿ',
    ('thó̤iⁿ i kâi chêng-cŭang', 'see how he appears.', '96'): 'thóiⁿ i kâi chêng-cŭang',
    ('lan̂g cúi', 'pus.', '97'): 'lâng cúi',
    ('thó̤iⁿ huang-cúi', 'to consider the geomantic influence.', '97'): 'thóiⁿ huang-cúi',
    ('keng cúi', 'thien kùi cúi; the menstrual flow.', '97'): 'keng cúi; thien kùi cúi',
    ('cuì-ong', 'boozy.', '98'): 'cùi-ong',
    ('lím cun', 'lím-lím cun; conform exactly.', '98'): 'lím cun; lím-lím cun',
    ('năi kàu kú-kú wń-wń kâi sṳ̄', 'this is something that never ceases.', '640'): 'năi kàu kú-kú ẃn-ẃn kâi sṳ̄',
    ('wn̂', 'Because; on account of; an affinity, a recondite sympathy.', '640'): 'ŵn',
    ('cṳ-nîe hùe īa kàu khûn kàu khûn khṳ̀ thóiⁿ hì', 'the women folk go in squads to see the play.', '351'): 'cṳ-nîe hùe īa kàu khûn khṳ̀ thóiⁿ hì',
    ('tàⁿ cêk kùa tîh-tîh-tâp-tâp tâp-tâp, tàⁿ bŏi tit ŵn', 'chatted a whole half-day as fast as possible, and could not say half they wished to.', '568'): 'tàⁿ cêk kùa tîh-tîh-tâp-tâp, tàⁿ bŏi tit ŵn',
    ('màiⁿ khah huang- mâng', 'do not be too hurried.', '186'): 'màiⁿ khah huang-mâng',
    ('i cò̤ sṳ̄ íong- iak căi', 'he does things with effusion.', '209'): 'i cò̤ sṳ̄ íong-iak căi',
    ('jìo kàu ku-ā kâi cńg- kah hûn', 'scratched so as to leave several marks of the finger nails.', '228'): 'jìo kàu ku-ā kâi cńg-kah hûn',
    ('ko̤-îeh jṳ́ pô̤h- pô̤h', 'spread the ointment very thin.', '233'): 'ko̤-îeh jṳ́ pô̤h-pô̤h',
    ('kṳ́n kŭ kúi īeⁿ lói- mûeh sàng i', 'carefully prepare a number of presents to offer him.', '295'): 'kṳ́n kŭ kúi īeⁿ lói-mûeh sàng i',
    ('tâng mn̂g- khí-cá cîah kàu taⁿ tn̂g khang tó khang', 'since breakfast this morning my stomach has remained unfilled.', '319'): 'tâng mn̂g-khí-cá cîah kàu taⁿ tn̂g khang tó khang',
    ('cham- che lō kháu', 'cross-roads; the point where several roads meet.', '322'): 'cham-che lō kháu',
    ('khì-kŭ côi- cíaⁿ', 'the utensils are all in order.', '326'): 'khì-kŭ côi-cíaⁿ',
    ('sûi- sĭ lâu-tŏng tîeh, khiak sĭ cak sêng nâng cêk kĭaⁿ hó̤ sṳ̄', 'although it makes trouble, it really forwards a commendable object.', '330'): 'sûi-sĭ lâu-tŏng tîeh, khiak sĭ cak sêng nâng cêk kĭaⁿ hó̤ sṳ̄',
    ('tàⁿ lâi thìang- khùai căi', 'very sharply said.', '344'): 'tàⁿ lâi thìang-khùai căi',
    ('li-li- la-la kâi nâng', 'a slovenly lout.', '368'): 'li-li-la-la kâi nâng',
    ('phàu- thâi', 'a fort.', '472'): 'phàu-thâi',
    ('phèng- chíaⁿ hîen-jîn', 'engage a teacher.', '473'): 'phèng chíaⁿ hîen-jîn',
    ('i phêng-pêh bô̤ kù mēⁿ úa ; he scolded me with- out the least reason, chng-kháu íⁿ-keng phêng-hôk lío', 'the sore is already healed.', '473'): 'i phêng-pêh bô̤ kù mēⁿ úa ; he scolded me without the least reason, chng-kháu íⁿ-keng phêng-hôk lío',
    ('cí kâi nâng lău-káng- kìu cîah tê', 'this is an old and discriminating tea drinker.', '552'): 'cí kâi nâng lău-káng-kìu cîah tê',
}


_PAGE_MARKER_RE = re.compile(r"<!-- page:(\d+) -->")
_HEAD_LINE_RE = re.compile(
    r"^(- \*\*.+?\*\*\s+)(.+?)((?:\s+\([^)]*\))?(?:\s*—\s*(.*))?)$"
)
_EX_LINE_RE = re.compile(r"^(\s*- \*)(.+?)(\*(?:\s*—\s*(.*))?)$")


def _apply_correction(prefix: str, reading: str, suffix: str, gloss: str, replacement: str) -> str:
    if "; " in replacement and gloss:
        seg = replacement.split("; ")[-1].strip()
        if gloss.startswith(seg + "; "):
            return f"{prefix}{replacement}* — {gloss[len(seg) + 2:].strip()}"
    return f"{prefix}{replacement}{suffix}"


def fix_reading_corrections(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    page = ""
    for line in lines:
        pm = _PAGE_MARKER_RE.search(line.strip())
        if pm:
            page = pm.group(1)
            out.append(line)
            continue
        m = _HEAD_LINE_RE.match(line)
        if m:
            prefix, reading, suffix, gloss = m.groups()
            key = (
                _clean(generate_original(reading)),
                _clean(generate_modified(gloss or "")),
                page,
            )
            replacement = _BOOK_READING_CORRECTIONS.get(key)
            out.append(_apply_correction(prefix, reading, suffix, gloss, replacement) if replacement is not None else line)
            continue
        m = _EX_LINE_RE.match(line)
        if m:
            prefix, reading, suffix, gloss = m.groups()
            key = (
                _clean(generate_original(reading)),
                _clean(generate_modified(gloss or "")),
                page,
            )
            replacement = _BOOK_READING_CORRECTIONS.get(key)
            out.append(_apply_correction(prefix, reading, suffix, gloss, replacement) if replacement is not None else line)
            continue
        out.append(line)
    return "\n".join(out)


def _is_blank_or_marker(line: str) -> bool:
    s = line.strip()
    return s == "" or s.startswith("<!-- page:")


def reformat_entries(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        m = _HEADWORD_RE.match(s)
        if not m:
            if s == ";":
                i += 1
                continue
            out.append(lines[i])
            i += 1
            continue
        hanzi = m.group(1)
        latn = m.group(2) or ""
        nums = m.group(3) or ""
        trailing_phrase = ""
        defn = ""
        pre_head_markers: list[str] = []
        post_entry_markers: list[str] = []
        j = i + 1
        while j < n and _is_blank_or_marker(lines[j]):
            if lines[j].strip().startswith("<!-- page:"):
                pre_head_markers.append(lines[j])
            j += 1
        if j < n:
            cand = lines[j].strip()
            if cand.startswith("*") and not _HEADWORD_RE.match(cand):
                defn = cand.lstrip("*").strip()
                j += 1
        while j < n:
            s3 = lines[j].strip()
            if _is_blank_or_marker(lines[j]):
                if s3.startswith("<!-- page:"):
                    pre_head_markers.append(lines[j])
                j += 1
                continue
            if s3.startswith((";", ":", "*", "#", "-")):
                break
            defn = (defn + " " + s3).strip() if defn else s3
            j += 1
        examples: list[tuple[str, str] | str] = []
        if trailing_phrase:
            examples.append((trailing_phrase, ""))
        k = j
        while k < n:
            s2 = lines[k].strip()
            if _is_blank_or_marker(lines[k]):
                if s2.startswith("<!-- page:"):
                    post_entry_markers.append(lines[k])
                k += 1
                continue
            if s2.startswith(";"):
                phrase = s2.lstrip(";").strip().rstrip(";").strip()
                gloss = ""
                unterminated = bool(phrase) and not s2.endswith(";") and not phrase.startswith("---")
                cross_markers: list[str] = []
                kk = k + 1
                while kk < n and _is_blank_or_marker(lines[kk]):
                    if lines[kk].strip().startswith("<!-- page:"):
                        look = kk + 1
                        while look < n and _is_blank_or_marker(lines[look]):
                            look += 1
                        if look < n and lines[look].strip().startswith(":"):
                            post_entry_markers.append(lines[kk])
                        elif (
                            unterminated
                            and look < n
                            and lines[look].strip().endswith(";")
                            and not lines[look].strip().startswith((";", ":", "*", "#", "-"))
                        ):
                            cross_markers.append(lines[kk].strip())
                        else:
                            examples.append((phrase, ""))
                            examples.append(lines[kk].strip())
                            phrase = ""
                    kk += 1
                if kk < n and lines[kk].strip().startswith(":"):
                    gloss = lines[kk].strip().lstrip(":").strip()
                    kk += 1
                    while kk < n and _is_blank_or_marker(lines[kk]):
                        if lines[kk].strip().startswith("<!-- page:"):
                            post_entry_markers.append(lines[kk])
                        kk += 1
                    if kk < n:
                        nxt = lines[kk].strip()
                        if nxt and not nxt.startswith((";", ":", "*", "#", "-")):
                            look = kk + 1
                            while look < n and (lines[look].strip() == "" or lines[look].strip().startswith("<!-- page:")):
                                look += 1
                            if not (look < n and lines[look].strip().endswith(";") and not lines[look].strip().startswith((";", ":", "*", "#", "-"))):
                                gloss = (gloss + " " + nxt).strip()
                                kk += 1
                    k = kk
                else:
                    while kk < n:
                        if _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                if phrase:
                                    examples.append((phrase, ""))
                                examples.append(lines[kk].strip())
                                phrase = ""
                            kk += 1
                            continue
                        nxt = lines[kk].strip()
                        if nxt.startswith((";", ":", "*", "#", "-")):
                            break
                        if cross_markers and nxt.endswith(";"):
                            nxt = nxt.rstrip(";").strip()
                        if phrase.endswith("-"):
                            phrase = (phrase + nxt).strip()
                        else:
                            phrase = (phrase + " " + nxt).strip()
                        kk += 1
                        while kk < n and _is_blank_or_marker(lines[kk]):
                            if lines[kk].strip().startswith("<!-- page:"):
                                post_entry_markers.append(lines[kk])
                            kk += 1
                        if kk < n and lines[kk].strip().startswith(":"):
                            gloss = lines[kk].strip().lstrip(":").strip()
                            kk += 1
                            while kk < n and _is_blank_or_marker(lines[kk]):
                                if lines[kk].strip().startswith("<!-- page:"):
                                    post_entry_markers.append(lines[kk])
                                kk += 1
                            break
                    k = kk
                examples.extend(cross_markers)
                examples.append((phrase, gloss))
            elif s2.startswith(":"):
                k += 1
            else:
                break
        merged: list[tuple[str, str] | str] = []
        for item in examples:
            if isinstance(item, tuple) and re.fullmatch(r"\d+", item[0]):
                if merged and isinstance(merged[-1], tuple):
                    ph, gl = merged[-1]
                    merged[-1] = (ph, (gl + " " + item[0]).strip() if gl else item[0])
                elif defn:
                    defn = (defn + " " + item[0]).strip()
                else:
                    merged.append(item)
            else:
                merged.append(item)
        examples = merged
        out.extend(pre_head_markers)
        head = f"- **{hanzi}** {latn} {nums}"
        if defn:
            head += f" — {defn}"
        out.append(head)
        for item in examples:
            if isinstance(item, str):
                out.append(item)
            else:
                ph, gl = item
                if gl:
                    out.append(f"  - *{ph}* — {gl}")
                else:
                    out.append(f"  - *{ph}*")
        out.extend(post_entry_markers)
        i = k
    return "\n".join(out)


def convert_section_titles(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    in_body = False
    pending_title: str | None = None
    while i < n:
        s = lines[i].strip()
        if not in_body:
            if s == "PREFACE.":
                in_body = True
                out.append(f"## {s}")
            else:
                out.append(lines[i])
            i += 1
            continue
        if pending_title is not None:
            if s == "":
                out.append("")
                i += 1
                continue
            if s == "of the":
                pending_title += " OF THE"
                i += 1
                continue
            if s.startswith("SWATOW DIALECT"):
                out.append(f"## {pending_title} SWATOW DIALECT.")
                pending_title = None
                i += 1
                continue
            out.append(f"## {pending_title}")
            pending_title = None
            continue
        if s == "ALPHABETIC DICTIONARY":
            pending_title = s
            i += 1
            continue
        if s in ("Vowels.", "Consonants."):
            out.append(f"**{s}**")
            i += 1
            continue
        if s == "The radicals.—jī-bó̤.":
            out.append(f"### {s}")
            i += 1
            continue
        if s and s.endswith(".") and s == s.upper() and len(s) > 3 \
                and not s.startswith(("-", "*", "#", ";", ":", "|")) \
                and not re.match(r"^\d", s):
            level = 2 if s in ("PREFACE.", "INTRODUCTION.") else 3
            out.append(f"{'#' * level} {s}")
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def fix_puj_ocr_digits(text: str, title: str) -> str:
    fixes = {**_PUJ_OCR_FIXES, **_BOOK_PUJ_OCR_FIXES.get(title, {})}
    for wrong, correct in fixes.items():
        text = text.replace(wrong, correct)
    return text


def postprocess(text: str, title: str = "") -> str:
    text = fix_puj_ocr_digits(text, title)
    out = reformat_entries(text)
    out = fix_orphaned_semicolons(out)
    out = convert_section_titles(out)
    out = cleanup(out)
    out = fix_reading_corrections(out)
    out = _HYPHEN_SPACE_RE.sub("-", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"(?:\n---\n){2,}", "\n---\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"
