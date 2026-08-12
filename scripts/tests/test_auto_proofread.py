from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIELDNAMES = [
    "斐_line",
    "词条",
    "读音",
    "讀音檢查",
    "007_puj_orig",
    "diff_聲母",
    "diff_韻母",
    "diff_聲調",
    "diff_音節數",
    "diff_第六調",
    "diff_連字號",
    "diff_標調符號",
    "diff_拼寫",
    "diff_詳情",
]


class TestAutoProofread(unittest.TestCase):
    def test_only_hyphen_only_rows_adopt_007_reading(self) -> None:
        rows = [
            {
                "斐_line": "57",
                "007_puj_orig": "á cîh",
                "diff_連字號": "Y",
            },
            {
                "斐_line": "55",
                "007_puj_orig": "bûa-a-bûa cū chûntíam-kíaⁿ",
                "diff_韻母": "Y",
                "diff_連字號": "Y",
            },
            {
                "斐_line": "58",
                "读音": "à chùi",
                "007_puj_orig": "à chùi",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 2/3",
            },
            {
                "斐_line": "9001",
                "007_puj_orig": "nŏ̤ nâng khṳ̀ kio i sie-hŭ chǐm",
                "diff_第六調": "Y",
            },
            {
                "斐_line": "17720",
                "007_puj_orig": "thi-ⁿě jío-lw̆n",
                "diff_韻母": "Y",
                "diff_第六調": "Y",
                "diff_連字號": "Y",
            },
            {
                "斐_line": "9002",
                "007_puj_orig": "chǐm a",
                "diff_第六調": "Y",
                "diff_連字號": "Y",
            },
            {
                "斐_line": "98",
                "007_puj_orig": "uá",
                "diff_標調符號": "Y",
            },
            {
                "斐_line": "957",
                "007_puj_orig": "līo",
                "diff_標調符號": "Y",
            },
            {
                "斐_line": "1398",
                "007_puj_orig": "bô̤ hièⁿ",
                "diff_標調符號": "Y",
            },
            {
                "斐_line": "6665",
                "007_puj_orig": "lan̂g",
                "diff_標調符號": "Y",
            },
            {
                "斐_line": "14468",
                "007_puj_orig": "cí chù bô̤ hue, pât chù chái",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ổ̤/ô̤",
            },
            {
                "斐_line": "276",
                "007_puj_orig": "lṳ́ àiⁿ tńg-khṳ̀ có-ke a būe",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: ṳ̤́/ur; 聲調: 1/2",
            },
            {
                "斐_line": "286",
                "007_puj_orig": "i kâi sim lăi sĭ àiⁿ, chùi m̄ káⁿ tàⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: an/ann",
            },
            {
                "斐_line": "294",
                "007_puj_orig": "ak tîeh i kâi piⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: in/inn",
            },
            {
                "斐_line": "240",
                "读音": "úa thiaⁿ-kìⁿ i cong-kú tó̤ ái, ái",
                "007_puj_orig": "áa thiaⁿ-kìⁿ i cong-kú tó̤ ái, ái",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ua/aa",
            },
            {
                "斐_line": "155",
                "读音": "tāu-saⁿ āⁿ",
                "007_puj_orig": "tāu-sa ⁿāⁿ",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_連字號": "Y",
                "diff_詳情": (
                    "連字號: 分隔形式不同; 聲母: /n; "
                    "韻母: au-sann/au-sa, ann/nann"
                ),
            },
            {
                "斐_line": "61",
                "读音": "à chíu pà",
                "讀音檢查": "讀音不符字目(拗=á)",
                "007_puj_orig": "á chíu pà",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 3/2",
            },
            {
                "斐_line": "2586",
                "读音": "cúi cŭ tŏ̤ kò̤̍, bŏi cáu",
                "讀音檢查": "多聲調(kò̤̍)",
                "007_puj_orig": "cúi cŭ tŏ̤ kò̤, bŏi cáu",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ò̤̍/ò̤",
            },
            {
                "斐_line": "3612",
                "读音": "cí câng chī̄u",
                "讀音檢查": "多聲調(chī̄u)",
                "007_puj_orig": "cí câng chīu",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: ī̄u/iu; 聲調: 1/7",
            },
            {
                "斐_line": "3896",
                "读音": "cìn tŏ̤ i sin-piⁿ",
                "007_puj_orig": "cìⁿ tŏ̤ i sin-piⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: cin/cinn",
            },
            {
                "斐_line": "1593",
                "读音": "màin bûa khah thíam",
                "007_puj_orig": "màiⁿ bûa khah thíam",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ain/ainn",
            },
            {
                "斐_line": "499",
                "读音": "màin khṳt i kuen",
                "007_puj_orig": "màiⁿ khṳt i kueⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ain/ainn, uen/uenn",
            },
            {
                "斐_line": "4717",
                "读音": "cía tîeh cang kha pa-cíeⁿn lâi phah",
                "讀音檢查": "讀音不符字目(掌=cíeⁿ)",
                "007_puj_orig": "cía tîeh cang kha pa-cíeⁿ lâi phah",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: a-ciennn/a-cienn",
            },
            {
                "斐_line": "73",
                "读音": "chíu-cn̄g-thâu á jîp, bô̤ á chut",
                "007_puj_orig": "chíu-cńg-thâu á jîp, bô̤ á chut",
                "diff_拼寫": "Y",
                "diff_詳情": "拼寫/標點差異",
            },
            {
                "斐_line": "74",
                "读音": "chíu-cn̄g-thâu",
                "007_puj_orig": "chíu-cńg-thâu",
                "diff_聲調": "Y",
                "diff_拼寫": "Y",
                "diff_詳情": "聲調: 7/2; 拼寫/標點差異",
            },
            {
                "斐_line": "1206",
                "读音": "tûi bît",
                "007_puj_orig": "túi bît",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 5/2",
            },
            {
                "斐_line": "23307",
                "读音": "úa íⁿ-keng thâk cêk kûe",
                "讀音檢查": "讀音不符字目(过=kùe)",
                "007_puj_orig": "úa íⁿ-keng thâk cêk kùe",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 5/3",
            },
            {
                "斐_line": "5530",
                "读音": "ìn cńg-thâu bô",
                "007_puj_orig": "ìu cńg-thâu bô",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: in/iu",
            },
            {
                "斐_line": "914",
                "读音": "báu jît, báu gûeh, báu nî",
                "007_puj_orig": "báu jît, báu gûeh, bán nî",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: au/an",
            },
            {
                "斐_line": "20573",
                "读音": "i kâi sṳ̄ kĭaⁿ cōi",
                "007_puj_orig": "i kâi ṳ̄ kĭaⁿ cōi",
                "diff_聲母": "Y",
                "diff_詳情": "聲母: s/",
            },
            {
                "斐_line": "8007",
                "读音": "ŭ kâi nâng lâi hìen cheh",
                "007_puj_orig": "ŭ kâi nâug lâi hìen cheh",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ang/aug",
            },
            {
                "斐_line": "6882",
                "读音": "cò̤-sṳ̄ màiⁿ cut",
                "007_puj_orig": "cò̤-sṳ̄ màiⁿ cháu cut",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_音節數": "Y",
                "diff_聲調": "Y",
                "diff_詳情": (
                    "音節數不同: (3 vs 4); 聲母: /ch; "
                    "韻母: cut/au; 聲調: 4/2"
                ),
            },
            {
                "斐_line": "835",
                "读音": "bâi mó̤ⁿ",
                "007_puj_orig": "bâi mô̤ⁿ",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 2/5",
            },
            {
                "斐_line": "392",
                "读音": "lú ŏi ùi àm a bŏi ?",
                "007_puj_orig": "lṳ́ ŏi ùi àm a bŏi",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: u/ur",
            },
            {
                "斐_line": "13673",
                "读音": "chin hu",
                "007_puj_orig": "chin hṳ́",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: u/ur; 聲調: 1/2",
            },
            {
                "斐_line": "27864",
                "读音": "seng-lí",
                "007_puj_orig": "seng-ĺi",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 1/2",
            },
            {
                "斐_line": "548",
                "读音": "hún âng",
                "007_puj_orig": "hún ang",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 5/1",
            },
            {
                "斐_line": "99",
                "读音": "lṳ́ ā, ĕ tng m̄ hó̤ cìeⁿ-seⁿ ā",
                "007_puj_orig": "lṳ́ ā, ĕ tńg m̄ hó̤ cìeⁿ-seⁿ ā",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 1/2",
            },
            {
                "斐_line": "265",
                "读音": "chin âi",
                "007_puj_orig": "bó̤ chin",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "聲母: ch/b, /ch; 韻母: in/o̤, ai/in; 聲調: 1/2, 5/1",
            },
            {
                "斐_line": "344",
                "读音": "hûe-sīeⁿ bô̤ seng-lí thiah am lêng-ūaⁿ khí",
                "007_puj_orig": "hûe-sīeⁿ bô seng-lí thiah am lêng-ūaⁿ khí",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: o̤/o",
            },
            {
                "斐_line": "4910",
                "读音": "kòng ciensìn cien",
                "007_puj_orig": "hue cien",
                "diff_音節數": "Y",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": (
                    "音節數不同: (3 vs 2); 聲母: k/h; "
                    "韻母: ong/ue; 聲調: 3/1"
                ),
            },
            {
                "斐_line": "28421",
                "读音": "lîen hŵn, kòi-cheh",
                "007_puj_orig": "lîen mŵn, kòi-cheh",
                "diff_聲母": "Y",
                "diff_詳情": "聲母: h/m",
            },
            {
                "斐_line": "1660",
                "读音": "cîah",
                "007_puj_orig": "ciah",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 8/4",
            },
            {
                "斐_line": "1715",
                "读音": "hṳ́",
                "007_puj_orig": "hú",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ur/u",
            },
            {
                "斐_line": "20503",
                "读音": "lô̤h",
                "007_puj_orig": "lôh",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: o̤h/oh",
            },
            {
                "斐_line": "28410",
                "读音": "chù-thâu sie lîen",
                "007_puj_orig": "chà-thâu sie lîen",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: u-thau/a-thau",
            },
            {
                "斐_line": "29814",
                "读音": "lw̆n sì kâi sî-hāu",
                "007_puj_orig": "lw̆n sì kâi sî-kāu",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: i-hau/i-kau",
            },
            {
                "斐_line": "29842",
                "读音": "i cò̤-nî m̆ ?",
                "007_puj_orig": "i cò-nî m̆",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: co̤-ni/co-ni",
            },
            {
                "斐_line": "29864",
                "读音": "m̄ kûiⁿ m̄ kĕ",
                "007_puj_orig": "m̄ kûi m̄ kĕ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: uinn/ui",
            },
            {
                "斐_line": "48006",
                "读音": "ui miⁿ-miⁿ",
                "007_puj_orig": "ni miⁿ-miⁿ",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_詳情": "聲母: /n; 韻母: ui/i",
            },
            {
                "斐_line": "46864",
                "读音": "thô̤aⁿ-hieⁿ",
                "007_puj_orig": "thôaⁿ-hieⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: o̤ann/uann",
            },
            {
                "斐_line": "2028",
                "读音": "i kâi hieⁿ-lí pun tek câh miⁿ-miⁿ",
                "007_puj_orig": "i kâi hieⁿ-lí puu tek câh miⁿ-miⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: un/uu",
            },
            {
                "斐_line": "47238",
                "词条": "我张梯在墙块",
                "读音": "úa tieⁿ thui tŏ̤ chîeⁿ kò̤",
                "007_puj_orig": "úa thieⁿ thui tŏ̤ chîeⁿ kò̤",
                "diff_聲母": "Y",
                "diff_詳情": "聲母: t/th",
            },
            {
                "斐_line": "47546",
                "读音": "uaⁿ hūn síu kí",
                "007_puj_orig": "uaⁿ hūu sĭu kí",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: un/uu; 聲調: 2/6",
            },
            {
                "斐_line": "46310",
                "读音": "i ío thiaⁿ nâng tà",
                "007_puj_orig": "i ío thiaⁿ̀ nâng tàⁿ",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: a/ann; 聲調: 1/3",
            },
            {
                "斐_line": "1227",
                "读音": "âu bó",
                "007_puj_orig": "ău bó",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 5/6",
            },
            {
                "斐_line": "2344",
                "读音": "tŏ̤ cí-kò̤ kàu hṳ́-kò̤ ŭ kúi căm lō",
                "007_puj_orig": "tŏ̤ cí-kò̤ kàu hṳ́-kò̤ ŭ kúi căm lō̤",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: o/o̤",
            },
            {
                "斐_line": "28160",
                "读音": "cîah lô̤h khṳ̀ bô̤ lîam bô sìam",
                "007_puj_orig": "ciah lô̤h khṳ̂ bô̤ lîam bô̤ sìam",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: o/o̤; 聲調: 8/4, 3/5",
            },
            {
                "斐_line": "40910",
                "读音": "bổ̤ sṳ-phiⁿ; bô̤ sṳ bô phiⁿ",
                "007_puj_orig": "bô̤ sṳ-phiⁿ; bô̤ sṳ bô̤ phiⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ỏ̤/o̤, o/o̤",
            },
            {
                "斐_line": "40689",
                "读音": "kak-kak sûi só̤ hàuⁿ",
                "007_puj_orig": "kak-kak sûi só̤ hànⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: aunn/annn",
            },
            {
                "斐_line": "773",
                "读音": "thàng kău hṳ́ ău-ău",
                "007_puj_orig": "thàng kàu hṳ́ ău-ău",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 6/3",
            },
            {
                "斐_line": "493",
                "读音": "khùai-hia kâi hia-àng sĭ lăi níu kâi",
                "007_puj_orig": "khùai-hia kâi hia-àng sĭ lâi níu kâi",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 6/5",
            },
            {
                "斐_line": "10877",
                "读音": "si-kue ùi bá gê",
                "007_puj_orig": "si-kùe ùi bà gê",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 1/3, 2/3",
            },
            {
                "斐_line": "1910",
                "读音": "cêk pńg, bw̄n lāi",
                "007_puj_orig": "cêk pńg, bw̄n lâi",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 7/5",
            },
            {
                "斐_line": "242",
                "读音": "i sĭ ai-kìe ka-kī kâi sṳ̄",
                "007_puj_orig": "i sĭ ái-kìe pât nâng kâi sṳ̄",
                "diff_聲母": "Y",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_音節數": "Y",
                "diff_詳情": (
                    "音節數不同: (19 vs 13); 聲母: k/p; "
                    "韻母: a-ki/at; 聲調: 1/2, 1/8, 7/5"
                ),
            },
            {
                "斐_line": "41518",
                "读音": "tam-ĭen ke kúi jĭt",
                "007_puj_orig": "tam-ĭen ke kúi jît",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 6/8",
            },
            {
                "斐_line": "859",
                "读音": "bâk-chieⁿ",
                "007_puj_orig": "bâk-chīeⁿ",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 1/7",
            },
            {
                "斐_line": "28",
                "读音": "lō pun cò̤ nŏ̤ a",
                "007_puj_orig": "lŏ pun cò̤ nŏ̤ a",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 7/6",
            },
            {
                "斐_line": "42804",
                "读音": "tī̄aⁿ",
                "007_puj_orig": "tīaⁿ",
                "diff_拼寫": "Y",
                "diff_詳情": "拼寫/標點差異",
            },
            {
                "斐_line": "42812",
                "读音": "chûn cêk kùa tīaⁿ-tīaⁿ",
                "007_puj_orig": "chûn cêk kùe tīaⁿ-tīaⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ua/ue",
            },
            {
                "斐_line": "39905",
                "读音": "tău-thâi sĭ kẃn-lí jîh-sì sôk",
                "007_puj_orig": "tău-thâi sĭ kẃn-lí jît-sì sôk",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ih/it",
            },
            {
                "斐_line": "12661",
                "读音": "cí pńg cheh jîeh cōi hîeh ?",
                "007_puj_orig": "cí pńg cheh jîeh cōi hĭeh",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 8/6",
            },
            {
                "斐_line": "519",
                "读音": "bô̤ nâng àng i hìeⁿ m̄ bó̤",
                "007_puj_orig": "bô̤ nâng àng i hìeⁿ m̄ hó̤",
                "diff_聲母": "Y",
                "diff_詳情": "聲母: b/h",
            },
            {
                "斐_line": "42100",
                "读音": "kha teⁿ, kha ău toⁿ",
                "007_puj_orig": "kha teⁿ; kha ău teⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: onn/enn",
            },
            {
                "斐_line": "6240",
                "读音": "cí īeⁿ îeh cú-tì sĭm-mih pē ?",
                "007_puj_orig": "cí īeⁿ îeh cú-tì sĭm-mih pēⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: e/enn",
            },
            {
                "斐_line": "41725",
                "读音": "hieⁿ tàng; hieⁿ sùaⁿ tâng",
                "007_puj_orig": "hieⁿ tâng; hieⁿ sùⁿ tâng",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: uann/unn; 聲調: 3/5",
            },
            {
                "斐_line": "7307",
                "读音": "tăi chut nâng châi kâi sî-hāu",
                "007_puj_orig": "tău chut nâng châi kâi sî-hāu",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ai/au",
            },
            {
                "斐_line": "41410",
                "读音": "kàng tăi sṳ̄",
                "007_puj_orig": "kàn tăi sṳ̄",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: ang/an",
            },
            {
                "斐_line": "41090",
                "词条": "赈唔济事",
                "读音": "cín m̄ cì sṳ̄",
                "007_puj_orig": "cía m̄ cì sṳ̄",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: cin/cia",
            },
            {
                "斐_line": "244",
                "读音": "cía sǹg sĭ ái-mŭe kâi sṳ̄",
                "007_puj_orig": "cía sǹg sĭ ái-mŭe kâi sṳ",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 7/1",
            },
            {
                "斐_line": "1499",
                "读音": "eng-hîong bô̤ eng-bú cṳ tī",
                "007_puj_orig": "eng-hîong bô̤ eng-bú cṳ tí",
                "diff_聲調": "Y",
                "diff_詳情": "聲調: 7/2",
            },
            {
                "斐_line": "10977",
                "读音": "cí sang ôi hìeⁿ tăng chēng lío chiu-chĭeⁿ",
                "007_puj_orig": "cí sang ôi hìeⁿ tăng chēng lío chin-chĭeⁿ",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: iu/in",
            },
            {
                "斐_line": "391",
                "读音": "sin-gî sen àm kúi",
                "007_puj_orig": "sim-gî seⁿ àm kúi",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: in/im, en/enn",
            },
            {
                "斐_line": "33104",
                "读音": "ô̤h u cêk īe kang-hu chíu-gōi tŏ̤ sin",
                "007_puj_orig": "ô̤h ŭ cêk īeⁿ kang-hu chíu-gōi tŏ̤ sin",
                "diff_韻母": "Y",
                "diff_聲調": "Y",
                "diff_詳情": "韻母: ie/ienn; 聲調: 1/6",
            },
            {
                "斐_line": "32427",
                "读音": "cía tê sek ngṳ̂n cêk níe",
                "007_puj_orig": "cíe tê sek ngṳ̂n cêk níe",
                "diff_韻母": "Y",
                "diff_詳情": "韻母: cia/cie",
            },
        ]
        for row in rows:
            for field in FIELDNAMES:
                row.setdefault(field, "")

        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            input_path = directory_path / "input.csv"
            output_path = directory_path / "output.csv"
            with input_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(rows)

            result = subprocess.run(
                [
                    sys.executable,
                    "auto_proofread.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with output_path.open(encoding="utf-8", newline="") as file:
                output_rows = list(csv.DictReader(file))

        self.assertEqual(
            list(output_rows[0]),
            [*FIELDNAMES, "校對_puj", "校對_詞條", "校對_來源"],
        )
        self.assertEqual(output_rows[0]["校對_puj"], "á cîh")
        self.assertEqual(output_rows[1]["校對_puj"], "")
        self.assertEqual(output_rows[2]["校對_puj"], "à chùi")
        self.assertEqual(
            output_rows[3]["校對_puj"],
            "nŏ̤ nâng khṳ̀ kio i sie-hŭ chĭm",
        )
        self.assertEqual(output_rows[4]["校對_puj"], "")
        self.assertEqual(output_rows[5]["校對_puj"], "chĭm a")
        self.assertEqual(output_rows[6]["校對_puj"], "úa")
        self.assertEqual(output_rows[7]["校對_puj"], "līo")
        self.assertEqual(output_rows[8]["校對_puj"], "bô̤ hìeⁿ")
        self.assertEqual(output_rows[9]["校對_puj"], "lâng")
        self.assertEqual(
            output_rows[10]["校對_puj"],
            "cí chù bô̤ hue, pât chù chái",
        )
        self.assertEqual(
            output_rows[11]["校對_puj"],
            "lṳ́ àiⁿ tńg-khṳ̀ có-ke a būe",
        )
        self.assertEqual(
            output_rows[12]["校對_puj"],
            "i kâi sim lăi sĭ àiⁿ, chùi m̄ káⁿ tàⁿ",
        )
        self.assertEqual(output_rows[13]["校對_puj"], "ak tîeh i kâi piⁿ")
        self.assertEqual(
            output_rows[14]["校對_puj"],
            "úa thiaⁿ-kìⁿ i cong-kú tó̤ ái, ái",
        )
        self.assertEqual(output_rows[15]["校對_puj"], "tāu-saⁿ āⁿ")
        self.assertEqual(output_rows[16]["校對_puj"], "à chíu pà")
        self.assertEqual(
            output_rows[17]["校對_puj"],
            "cúi cŭ tŏ̤ kò̤, bŏi cáu",
        )
        self.assertEqual(output_rows[18]["校對_puj"], "cí câng chīu")
        self.assertEqual(output_rows[19]["校對_puj"], "cìⁿ tŏ̤ i sin-piⁿ")
        self.assertEqual(output_rows[20]["校對_puj"], "màiⁿ bûa khah thíam")
        self.assertEqual(output_rows[21]["校對_puj"], "")
        self.assertEqual(
            output_rows[22]["校對_puj"],
            "cía tîeh cang kha pa-cíeⁿ lâi phah",
        )
        self.assertEqual(
            output_rows[23]["校對_puj"],
            "chíu-cn̄g-thâu á jîp, bô̤ á chut",
        )
        self.assertEqual(output_rows[24]["校對_puj"], "chíu-cn̄g-thâu")
        self.assertEqual(output_rows[25]["校對_puj"], "tûi bît")
        self.assertEqual(
            output_rows[26]["校對_puj"],
            "úa íⁿ-keng thâk cêk kûe",
        )
        self.assertEqual(output_rows[27]["校對_puj"], "ìn cńg-thâu bô")
        self.assertEqual(
            output_rows[28]["校對_puj"],
            "báu jît, báu gûeh, báu nî",
        )
        self.assertEqual(output_rows[29]["校對_puj"], "i kâi sṳ̄ kĭaⁿ cōi")
        self.assertEqual(
            output_rows[30]["校對_puj"],
            "ŭ kâi nâng lâi hìen cheh",
        )
        self.assertEqual(output_rows[31]["校對_puj"], "cò̤-sṳ̄ màiⁿ cut")
        self.assertEqual(output_rows[32]["校對_puj"], "bâi mó̤ⁿ")
        self.assertEqual(output_rows[33]["校對_puj"], "lṳ́ ŏi ùi àm a bŏi")
        self.assertEqual(output_rows[34]["校對_puj"], "chin hṳ́")
        self.assertEqual(output_rows[35]["校對_puj"], "seng-lí")
        self.assertEqual(output_rows[36]["校對_puj"], "hún âng")
        self.assertEqual(
            output_rows[37]["校對_puj"],
            "lṳ́ ā, ĕ tńg m̄ hó̤ cìeⁿ-seⁿ ā",
        )
        self.assertEqual(output_rows[38]["校對_puj"], "bó̤ chin")
        self.assertEqual(
            output_rows[39]["校對_puj"],
            "hûe-sīeⁿ bô̤ seng-lí thiah am lêng-ūaⁿ khí",
        )
        self.assertEqual(output_rows[40]["校對_puj"], "kòng ciensìn cien")
        self.assertEqual(output_rows[41]["校對_puj"], "lîen hŵn, kòi-cheh")
        self.assertEqual(output_rows[42]["校對_puj"], "cîah")
        self.assertEqual(output_rows[43]["校對_puj"], "hṳ́")
        self.assertEqual(output_rows[44]["校對_puj"], "lô̤h")
        self.assertEqual(output_rows[45]["校對_puj"], "chù-thâu sie lîen")
        self.assertEqual(output_rows[46]["校對_puj"], "lw̆n sì kâi sî-hāu")
        self.assertEqual(output_rows[47]["校對_puj"], "i cò̤-nî m̆ ?")
        self.assertEqual(output_rows[48]["校對_puj"], "m̄ kûiⁿ m̄ kĕ")
        self.assertEqual(output_rows[49]["校對_puj"], "ui miⁿ-miⁿ")
        self.assertEqual(output_rows[50]["校對_puj"], "thô̤aⁿ-hieⁿ")
        self.assertEqual(
            output_rows[51]["校對_puj"],
            "i kâi hieⁿ-lí pun tek câh miⁿ-miⁿ",
        )
        self.assertEqual(output_rows[52]["校對_puj"], "")
        self.assertEqual(output_rows[52]["校對_詞條"], "倚张梯在墙块")
        self.assertEqual(output_rows[53]["校對_puj"], "uaⁿ hūn síu kí")
        self.assertEqual(
            output_rows[54]["校對_puj"],
            "i ío thiaⁿ nâng tàⁿ",
        )
        self.assertEqual(output_rows[55]["校對_puj"], "âu bó")
        self.assertEqual(
            output_rows[56]["校對_puj"],
            "tŏ̤ cí-kò̤ kàu hṳ́-kò̤ ŭ kúi căm lō̤",
        )
        self.assertEqual(
            output_rows[57]["校對_puj"],
            "ciah lô̤h khṳ̂ bô̤ lîam bô̤ sìam",
        )
        self.assertEqual(
            output_rows[58]["校對_puj"],
            "bô̤ sṳ-phiⁿ; bô̤ sṳ bô̤ phiⁿ",
        )
        self.assertEqual(output_rows[59]["校對_puj"], "kak-kak sûi só̤ hàuⁿ")
        self.assertEqual(output_rows[60]["校對_puj"], "thàng kău hṳ́ ău-ău")
        self.assertEqual(
            output_rows[61]["校對_puj"],
            "khùai-hia kâi hia-àng sĭ lăi níu kâi",
        )
        self.assertEqual(output_rows[62]["校對_puj"], "si-kùe ùi bà gê")
        self.assertEqual(output_rows[63]["校對_puj"], "cêk pńg, bw̄n lāi")
        self.assertEqual(
            output_rows[64]["校對_puj"],
            "i sĭ ai-kìe ka-kī kâi sṳ̄",
        )
        self.assertEqual(
            output_rows[65]["校對_puj"],
            "tam-ĭen ke kúi jît",
        )
        self.assertEqual(output_rows[66]["校對_puj"], "bâk-chīeⁿ")
        self.assertEqual(output_rows[67]["校對_puj"], "lŏ pun cò̤ nŏ̤ a")
        self.assertEqual(output_rows[68]["校對_puj"], "tīaⁿ")
        self.assertEqual(
            output_rows[69]["校對_puj"],
            "chûn cêk kùa tīaⁿ-tīaⁿ",
        )
        self.assertEqual(
            output_rows[70]["校對_puj"],
            "tău-thâi sĭ kẃn-lí jîh-sì sôk",
        )
        self.assertEqual(
            output_rows[71]["校對_puj"],
            "cí pńg cheh jîeh cōi hîeh ?",
        )
        self.assertEqual(
            output_rows[72]["校對_puj"],
            "bô̤ nâng àng i hìeⁿ m̄ bó̤",
        )
        self.assertEqual(
            output_rows[73]["校對_puj"],
            "kha teⁿ; kha ău teⁿ",
        )
        self.assertEqual(
            output_rows[74]["校對_puj"],
            "cí īeⁿ îeh cú-tì sĭm-mih pēⁿ",
        )
        self.assertEqual(
            output_rows[75]["校對_puj"],
            "hieⁿ tàng; hieⁿ sùaⁿ tâng",
        )
        self.assertEqual(
            output_rows[76]["校對_puj"],
            "tăi chut nâng châi kâi sî-hāu",
        )
        self.assertEqual(output_rows[77]["校對_puj"], "kàng tăi sṳ̄")
        self.assertEqual(output_rows[78]["校對_puj"], "cía m̄ cì sṳ̄")
        self.assertEqual(output_rows[78]["校對_詞條"], "者唔济事")
        self.assertEqual(
            output_rows[79]["校對_puj"],
            "cía sǹg sĭ ái-mŭe kâi sṳ̄",
        )
        self.assertEqual(
            output_rows[80]["校對_puj"],
            "eng-hîong bô̤ eng-bú cṳ tī",
        )
        self.assertEqual(
            output_rows[81]["校對_puj"],
            "cí sang ôi hìeⁿ tăng chēng lío chin-chĭeⁿ",
        )
        self.assertEqual(
            output_rows[82]["校對_puj"],
            "sin-gî sen àm kúi",
        )
        self.assertEqual(
            output_rows[83]["校對_puj"],
            "ô̤h ŭ cêk īeⁿ kang-hu chíu-gōi tŏ̤ sin",
        )
        self.assertEqual(
            output_rows[84]["校對_puj"],
            "cía tê sek ngṳ̂n cêk níe",
        )


if __name__ == "__main__":
    unittest.main()
