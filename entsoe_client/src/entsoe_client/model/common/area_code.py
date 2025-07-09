import re
from enum import Enum
from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from src.entsoe_client.exceptions.unknown_area_code_error import UnknownAreaCodeError
from src.entsoe_client.model.common.area_type import AreaType


class AreaCode(Enum):
    NIE_SONI = (
        "10Y1001A1001A016",
        "CTA|NIE, MBA|SEM(SONI), SCA|NIE",
        "Northern Ireland",
    )
    ESTONIA = ("10Y1001A1001A39I", "SCA|EE, MBA|EE, CTA|EE, BZN|EE", "Estonia (EE)")
    SWEDEN_SE1 = (
        "10Y1001A1001A44P",
        "IPA|SE1, BZN|SE1, MBA|SE1, SCA|SE1",
        "Sweden SE1 ",
    )
    SWEDEN_SE2 = (
        "10Y1001A1001A45N",
        "SCA|SE2, MBA|SE2, BZN|SE2, IPA|SE2",
        "Sweden SE2 ",
    )
    SWEDEN_SE3 = (
        "10Y1001A1001A46L",
        "IPA|SE3, BZN|SE3, MBA|SE3, SCA|SE3",
        "Sweden SE3 ",
    )
    SWEDEN_SE4 = (
        "10Y1001A1001A47J",
        "SCA|SE4, MBA|SE4, BZN|SE4, IPA|SE4",
        "Sweden SE4 ",
    )
    NORWAY_NO5 = (
        "10Y1001A1001A48H",
        "IPA|NO5, IBA|NO5, BZN|NO5, MBA|NO5, SCA|NO5",
        "Norway NO5 ",
    )
    RUSSIA = ("10Y1001A1001A49F", "SCA|RU, MBA|RU, BZN|RU, CTA|RU", "Russia ")
    RUSSIA_KALININGRAD = (
        "10Y1001A1001A50U",
        "CTA|RU-KGD, BZN|RU-KGD, MBA|RU-KGD, SCA|RU-KGD",
        "Russia Kaliningrad ",
    )
    BELARUS = ("10Y1001A1001A51S", "SCA|BY, MBA|BY, BZN|BY, CTA|BY", "Belarus ")
    IRELAND_SEM = (
        "10Y1001A1001A59C",
        "BZN|IE(SEM), MBA|IE(SEM), SCA|IE(SEM), LFB|IE-NIE, SNA|Ireland",
        "Ireland SEM ",
    )
    DE_AT_LU = ("10Y1001A1001A63L", "BZN|DE-AT-LU", "Germany-Austria-Luxembourg ")
    NORWAY_NO1A = ("10Y1001A1001A64J", "BZN|NO1A", "Norway NO1A ")
    DENMARK = ("10Y1001A1001A65H", "Denmark (DK)", "Denmark ")
    IT_GR = ("10Y1001A1001A66F", "BZN|IT-GR", "Italy-Greece ")
    IT_NORTH_SI = ("10Y1001A1001A67D", "BZN|IT-North-SI", "Italy North-Slovenia ")
    IT_NORTH_CH = ("10Y1001A1001A68B", "BZN|IT-North-CH", "Italy North-Switzerland ")
    IT_BRINDISI = (
        "10Y1001A1001A699",
        "BZN|IT-Brindisi, SCA|IT-Brindisi, MBA|IT-Z-Brindisi",
        "Italy Brindisi ",
    )
    IT_CENTRE_NORTH = (
        "10Y1001A1001A70O",
        "MBA|IT-Z-Centre-North, SCA|IT-Centre-North, BZN|IT-Centre-North",
        "Italy Centre North ",
    )
    IT_CENTRE_SOUTH = (
        "10Y1001A1001A71M",
        "BZN|IT-Centre-South, SCA|IT-Centre-South, MBA|IT-Z-Centre-South",
        "Italy Centre South ",
    )
    IT_FOGGIA = (
        "10Y1001A1001A72K",
        "MBA|IT-Z-Foggia, SCA|IT-Foggia, BZN|IT-Foggia",
        "Italy Foggia ",
    )
    IT_NORTH = (
        "10Y1001A1001A73I",
        "BZN|IT-North, SCA|IT-North, MBA|IT-Z-North",
        "Italy North ",
    )
    IT_SARDINIA = (
        "10Y1001A1001A74G",
        "MBA|IT-Z-Sardinia, SCA|IT-Sardinia, BZN|IT-Sardinia",
        "Italy Sardinia ",
    )
    IT_SICILY = (
        "10Y1001A1001A75E",
        "BZN|IT-Sicily, SCA|IT-Sicily, MBA|IT-Z-Sicily",
        "Italy Sicily ",
    )
    IT_PRIOLO = (
        "10Y1001A1001A76C",
        "MBA|IT-Z-Priolo, SCA|IT-Priolo, BZN|IT-Priolo",
        "Italy Priolo ",
    )
    IT_ROSSANO = (
        "10Y1001A1001A77A",
        "BZN|IT-Rossano, SCA|IT-Rossano, MBA|IT-Z-Rossano",
        "Italy Rossano ",
    )
    IT_SOUTH = (
        "10Y1001A1001A788",
        "MBA|IT-Z-South, SCA|IT-South, BZN|IT-South",
        "Italy South ",
    )
    DENMARK_CTA = ("10Y1001A1001A796", "CTA|DK", "Denmark Control Area ")
    IT_NORTH_AT = ("10Y1001A1001A80L", "BZN|IT-North-AT", "Italy North-Austria ")
    IT_NORTH_FR = ("10Y1001A1001A81J", "BZN|IT-North-FR", "Italy North-France ")
    DE_LU = (
        "10Y1001A1001A82H",
        "BZN|DE-LU, IPA|DE-LU, SCA|DE-LU, MBA|DE-LU",
        "Germany-Luxembourg ",
    )
    GERMANY = ("10Y1001A1001A83F", "Germany (DE)", "Germany ")
    IT_MACROZONE_NORTH = (
        "10Y1001A1001A84D",
        "MBA|IT-MACRZONENORTH, SCA|IT-MACRZONENORTH",
        "Italy Macrozone North ",
    )
    IT_MACROZONE_SOUTH = (
        "10Y1001A1001A85B",
        "SCA|IT-MACRZONESOUTH, MBA|IT-MACRZONESOUTH",
        "Italy Macrozone South ",
    )
    UA_DOBTPP = (
        "10Y1001A1001A869",
        "SCA|UA-DobTPP, BZN|UA-DobTPP, CTA|UA-DobTPP",
        "Ukraine DobTPP ",
    )
    IT_MALTA = ("10Y1001A1001A877", "BZN|IT-Malta", "Italy-Malta ")
    IT_SACOAC = ("10Y1001A1001A885", "BZN|IT-SACOAC", "Italy SACOAC ")
    IT_SACODC = ("10Y1001A1001A893", "BZN|IT-SACODC, SCA|IT-SACODC", "Italy SACODC ")
    NORDIC = (
        "10Y1001A1001A91G",
        "SNA|Nordic, REG|Nordic, LFB|Nordic",
        "Nordic Region ",
    )
    UNITED_KINGDOM = ("10Y1001A1001A92E", "United Kingdom (UK)", "United Kingdom ")
    MALTA = ("10Y1001A1001A93C", "Malta (MT), BZN|MT, CTA|MT, SCA|MT, MBA|MT", "Malta ")
    MOLDOVA = ("10Y1001A1001A990", "MBA|MD, SCA|MD, CTA|MD, BZN|MD", "Moldova ")
    ARMENIA = ("10Y1001A1001B004", "Armenia (AM), BZN|AM, CTA|AM", "Armenia ")
    GEORGIA = (
        "10Y1001A1001B012",
        "CTA|GE, BZN|GE, Georgia (GE), SCA|GE, MBA|GE",
        "Georgia ",
    )
    AZERBAIJAN = ("10Y1001A1001B05V", "Azerbaijan (AZ), BZN|AZ, CTA|AZ", "Azerbaijan ")
    UKRAINE = ("10Y1001C--00003F", "BZN|UA, Ukraine (UA), MBA|UA, SCA|UA", "Ukraine ")
    UKRAINE_IPS = (
        "10Y1001C--000182",
        "SCA|UA-IPS, MBA|UA-IPS, BZN|UA-IPS, CTA|UA-IPS",
        "Ukraine IPS ",
    )
    CZ_DE_SK_LT_SE4 = (
        "10Y1001C--00038X",
        "BZA|CZ-DE-SK-LT-SE4",
        "Czech Republic-Germany-Slovakia-Lithuania-SE4 ",
    )
    CORE_REGION = ("10Y1001C--00059P", "REG|CORE", "Core Region ")
    AFRR_REGION = ("10Y1001C--00090V", "REG|AFRR, SCA|AFRR", "AFRR Region ")
    SWE_REGION = ("10Y1001C--00095L", "REG|SWE", "SWE Region ")
    IT_CALABRIA = (
        "10Y1001C--00096J",
        "SCA|IT-Calabria, MBA|IT-Z-Calabria, BZN|IT-Calabria",
        "Italy Calabria ",
    )
    GB_IFA = ("10Y1001C--00098F", "BZN|GB(IFA)", "Great Britain IFA ")
    KOSOVO = (
        "10Y1001C--00100H",
        "BZN|XK, CTA|XK, Kosovo (XK), MBA|XK, LFB|XK, LFA|XK",
        "Kosovo ",
    )
    INDIA = ("10Y1001C--00119X", "SCA|IN", "India ")
    NORWAY_NO2A = ("10Y1001C--001219", "BZN|NO2A", "Norway NO2A ")
    ITALY_NORTH_REG = ("10Y1001C--00137V", "REG|ITALYNORTH", "Italy North Region ")
    GRIT_REGION = ("10Y1001C--00138T", "REG|GRIT", "GRIT Region ")
    ALBANIA = (
        "10YAL-KESH-----5",
        "LFB|AL, LFA|AL, BZN|AL, CTA|AL, Albania (AL), SCA|AL, MBA|AL",
        "Albania ",
    )
    AUSTRIA = (
        "10YAT-APG------L",
        "MBA|AT, SCA|AT, Austria (AT), IPA|AT, CTA|AT, BZN|AT, LFA|AT, LFB|AT",
        "Austria ",
    )
    BOSNIA_HERZEGOVINA = (
        "10YBA-JPCC-----D",
        "LFA|BA, BZN|BA, CTA|BA, Bosnia and Herz. (BA), SCA|BA, MBA|BA",
        "Bosnia and Herzegovina ",
    )
    BELGIUM = (
        "10YBE----------2",
        "MBA|BE, SCA|BE, Belgium (BE), CTA|BE, BZN|BE, LFA|BE, LFB|BE",
        "Belgium ",
    )
    BULGARIA = (
        "10YCA-BULGARIA-R",
        "LFB|BG, LFA|BG, BZN|BG, CTA|BG, Bulgaria (BG), SCA|BG, MBA|BG",
        "Bulgaria ",
    )
    DE_DK1_LU = (
        "10YCB-GERMANY--8",
        "SCA|DE_DK1_LU, LFB|DE_DK1_LU",
        "Germany-Denmark1-Luxembourg ",
    )
    RS_MK_ME = ("10YCB-JIEL-----9", "LFB|RS_MK_ME", "Serbia-Macedonia-Montenegro ")
    POLAND_LFB = ("10YCB-POLAND---Z", "LFB|PL", "Poland LFB ")
    SI_HR_BA = ("10YCB-SI-HR-BA-3", "LFB|SI_HR_BA", "Slovenia-Croatia-Bosnia ")
    SWITZERLAND = (
        "10YCH-SWISSGRIDZ",
        "LFB|CH, LFA|CH, SCA|CH, MBA|CH, Switzerland (CH), CTA|CH, BZN|CH",
        "Switzerland ",
    )
    MONTENEGRO = (
        "10YCS-CG-TSO---S",
        "BZN|ME, CTA|ME, Montenegro (ME), MBA|ME, SCA|ME, LFA|ME",
        "Montenegro ",
    )
    SERBIA = (
        "10YCS-SERBIATSOV",
        "LFA|RS, SCA|RS, MBA|RS, Serbia (RS), CTA|RS, BZN|RS",
        "Serbia ",
    )
    CYPRUS = (
        "10YCY-1001A0003J",
        "BZN|CY, CTA|CY, Cyprus (CY), MBA|CY, SCA|CY",
        "Cyprus ",
    )
    CZECH_REPUBLIC = (
        "10YCZ-CEPS-----N",
        "SCA|CZ, MBA|CZ, Czech Republic (CZ), CTA|CZ, BZN|CZ, LFA|CZ, LFB|CZ",
        "Czech Republic ",
    )
    DE_TRANSNET_BW = (
        "10YDE-ENBW-----N",
        "LFA|DE(TransnetBW), CTA|DE(TransnetBW), SCA|DE(TransnetBW)",
        "Germany TransnetBW ",
    )
    DE_TENNET_GER = (
        "10YDE-EON------1",
        "SCA|DE(TenneT GER), CTA|DE(TenneT GER), LFA|DE(TenneT GER)",
        "Germany TenneT ",
    )
    DE_AMPRION = (
        "10YDE-RWENET---I",
        "LFA|DE(Amprion), CTA|DE(Amprion), SCA|DE(Amprion)",
        "Germany Amprion ",
    )
    DE_50HERTZ = (
        "10YDE-VE-------2",
        "SCA|DE(50Hertz), CTA|DE(50Hertz), LFA|DE(50Hertz), BZA|DE(50HzT)",
        "Germany 50Hertz ",
    )
    DENMARK_DK1A = ("10YDK-1-------AA", "BZN|DK1A", "Denmark DK1A ")
    DENMARK_DK1 = (
        "10YDK-1--------W",
        "IPA|DK1, IBA|DK1, BZN|DK1, SCA|DK1, MBA|DK1, LFA|DK1",
        "Denmark DK1 ",
    )
    DENMARK_DK2 = (
        "10YDK-2--------M",
        "LFA|DK2, MBA|DK2, SCA|DK2, IBA|DK2, IPA|DK2, BZN|DK2",
        "Denmark DK2 ",
    )
    PL_CZ = ("10YDOM-1001A082L", "CTA|PL-CZ, BZA|PL-CZ", "Poland-Czech Republic ")
    CZ_DE_SK = (
        "10YDOM-CZ-DE-SKK",
        "BZA|CZ-DE-SK, BZN|CZ+DE+SK",
        "Czech Republic-Germany-Slovakia ",
    )
    LT_SE4 = ("10YDOM-PL-SE-LT2", "BZA|LT-SE4", "Lithuania-Sweden SE4 ")
    CWE_REGION = ("10YDOM-REGION-1V", "REG|CWE", "Central Western Europe ")
    SPAIN = (
        "10YES-REE------0",
        "LFB|ES, LFA|ES, BZN|ES, Spain (ES), CTA|ES, SCA|ES, MBA|ES",
        "Spain ",
    )
    CONTINENTAL_EUROPE = (
        "10YEU-CONT-SYNC0",
        "SNA|Continental Europe",
        "Continental Europe ",
    )
    FINLAND = (
        "10YFI-1--------U",
        "MBA|FI, SCA|FI, CTA|FI, Finland (FI), BZN|FI, IPA|FI, IBA|FI",
        "Finland ",
    )
    FRANCE = (
        "10YFR-RTE------C",
        "BZN|FR, France (FR), CTA|FR, SCA|FR, MBA|FR, LFB|FR, LFA|FR",
        "France ",
    )
    GREAT_BRITAIN = (
        "10YGB----------A",
        "LFA|GB, LFB|GB, SNA|GB, MBA|GB, SCA|GB, CTA|National Grid, BZN|GB",
        "Great Britain ",
    )
    GREECE = (
        "10YGR-HTSO-----Y",
        "BZN|GR, Greece (GR), CTA|GR, SCA|GR, MBA|GR, LFB|GR, LFA|GR",
        "Greece ",
    )
    CROATIA = (
        "10YHR-HEP------M",
        "LFA|HR, MBA|HR, SCA|HR, CTA|HR, Croatia (HR), BZN|HR",
        "Croatia ",
    )
    HUNGARY = (
        "10YHU-MAVIR----U",
        "BZN|HU, Hungary (HU), CTA|HU, SCA|HU, MBA|HU, LFA|HU, LFB|HU",
        "Hungary ",
    )
    IRELAND = (
        "10YIE-1001A00010",
        "MBA|SEM(EirGrid), SCA|IE, CTA|IE, Ireland (IE)",
        "Ireland ",
    )
    ITALY = (
        "10YIT-GRTN-----B",
        "Italy (IT), CTA|IT, SCA|IT, MBA|IT, LFB|IT, LFA|IT",
        "Italy ",
    )
    LITHUANIA = (
        "10YLT-1001A0008Q",
        "MBA|LT, SCA|LT, CTA|LT, Lithuania (LT), BZN|LT",
        "Lithuania ",
    )
    LUXEMBOURG = ("10YLU-CEGEDEL-NQ", "Luxembourg (LU), CTA|LU", "Luxembourg ")
    LATVIA = (
        "10YLV-1001A00074",
        "CTA|LV, Latvia (LV), BZN|LV, SCA|LV, MBA|LV",
        "Latvia ",
    )
    NORTH_MACEDONIA = (
        "10YMK-MEPSO----8",
        "MBA|MK, SCA|MK, BZN|MK, North Macedonia (MK), CTA|MK, LFA|MK",
        "North Macedonia ",
    )
    NETHERLANDS = (
        "10YNL----------L",
        "LFA|NL, LFB|NL, CTA|NL, Netherlands (NL), BZN|NL, SCA|NL, MBA|NL",
        "Netherlands ",
    )
    NORWAY = ("10YNO-0--------C", "MBA|NO, SCA|NO, Norway (NO), CTA|NO", "Norway ")
    NORWAY_NO1 = (
        "10YNO-1--------2",
        "BZN|NO1, IBA|NO1, IPA|NO1, SCA|NO1, MBA|NO1",
        "Norway NO1 ",
    )
    NORWAY_NO2 = (
        "10YNO-2--------T",
        "MBA|NO2, SCA|NO2, IPA|NO2, IBA|NO2, BZN|NO2",
        "Norway NO2 ",
    )
    NORWAY_NO3 = (
        "10YNO-3--------J",
        "BZN|NO3, IBA|NO3, IPA|NO3, SCA|NO3, MBA|NO3",
        "Norway NO3 ",
    )
    NORWAY_NO4 = (
        "10YNO-4--------9",
        "MBA|NO4, SCA|NO4, IPA|NO4, IBA|NO4, BZN|NO4",
        "Norway NO4 ",
    )
    POLAND = (
        "10YPL-AREA-----S",
        "BZN|PL, Poland (PL), CTA|PL, SCA|PL, MBA|PL, BZA|PL, LFA|PL",
        "Poland ",
    )
    PORTUGAL = (
        "10YPT-REN------W",
        "LFA|PT, LFB|PT, MBA|PT, SCA|PT, CTA|PT, Portugal (PT), BZN|PT",
        "Portugal ",
    )
    ROMANIA = (
        "10YRO-TEL------P",
        "BZN|RO, Romania (RO), CTA|RO, SCA|RO, MBA|RO, LFB|RO, LFA|RO",
        "Romania ",
    )
    SWEDEN = ("10YSE-1--------K", "MBA|SE, SCA|SE, CTA|SE, Sweden (SE)", "Sweden ")
    SLOVENIA = (
        "10YSI-ELES-----O",
        "Slovenia (SI), BZN|SI, CTA|SI, SCA|SI, MBA|SI, LFA|SI",
        "Slovenia ",
    )
    SLOVAKIA = (
        "10YSK-SEPS-----K",
        "LFA|SK, LFB|SK, MBA|SK, SCA|SK, CTA|SK, BZN|SK, Slovakia (SK)",
        "Slovakia ",
    )
    TURKEY = (
        "10YTR-TEIAS----W",
        "Turkey (TR), BZN|TR, CTA|TR, SCA|TR, MBA|TR, LFB|TR, LFA|TR",
        "Turkey ",
    )
    UKRAINE_BEI = (
        "10YUA-WEPS-----0",
        "LFA|UA-BEI, LFB|UA-BEI, MBA|UA-BEI, SCA|UA-BEI, CTA|UA-BEI, BZN|UA-BEI",
        "Ukraine BEI ",
    )
    GB_ELECLINK = ("11Y0-0000-0265-K", "BZN|GB(ElecLink)", "Great Britain ElecLink ")
    GB_IFA2 = ("17Y0000009369493", "BZN|GB(IFA2)", "Great Britain IFA2 ")
    DK1_NO1 = ("46Y000000000007M", "BZN|DK1-NO1", "Denmark DK1-Norway NO1 ")
    NO2NSL = ("50Y0JVU59B4JWQCU", "BZN|NO2NSL", "Norway NO2NSL ")
    BELARUS_SHORT = ("BY", "Belarus (BY)", "Belarus ")
    RUSSIA_SHORT = ("RU", "Russia (RU)", "Russia ")
    ICELAND = ("IS", "Iceland (IS)", "Iceland")

    def __init__(self, code: str, area_types: str, description: str) -> None:
        self.code = code
        self.area_types = area_types
        self.description = description

    @classmethod
    def from_code(cls, code: str) -> Self:
        for member in cls:
            if member.code == code:
                return member
        raise UnknownAreaCodeError(code)

    def _safe_from_code(self, code: str) -> Self | None:
        try:
            return self.from_code(code)
        except UnknownAreaCodeError:
            return None

    def get_area_types_list(self) -> list[AreaType]:
        return list(
            filter(
                lambda x: x is not None,
                map(
                    self._safe_from_code,
                    {
                        part.split("|")[0]
                        for part in self.area_types.split(", ")
                        if "|" in part
                    },
                ),
            ),
        )

    def has_area_type(self, area_type: AreaType) -> bool:
        return area_type in self.get_area_types_list()

    def get_country_code(self) -> str | None:
        # 1. Regex search for a code after a pipe '|' in area_types_str
        # Looks for a literal pipe, then captures two uppercase letters.
        match = re.search(r"\|([A-Z]{2})", self.area_types)
        if match:
            return match.group(1)

        # 2. If not found, regex search for a code in parentheses '(..)' in area_types_str
        # Looks for a literal '(', then captures two word characters, then a literal ')'
        match = re.search(r"\((\w{2})\)", self.area_types)
        if match:
            return match.group(1)

        # 3. Finally, try the same search in the description string
        match = re.search(r"\((\w{2})\)", self.description)
        if match:
            return match.group(1)

        # 4. If no code is found in any of the sources, return None
        return None

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        from_code_validator = core_schema.no_info_plain_validator_function(
            cls.from_code,
        )

        return core_schema.json_or_python_schema(
            json_schema=from_code_validator,
            # For creating models from Python, we can be more flexible:
            # allow passing an existing AreaCode instance OR a string to be parsed.
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_code_validator],
            ),
            # For serialization (e.g., model_dump), define the 'marshal' logic.
            # We take an AreaCode instance and return its .code attribute.
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.code,
            ),
        )
