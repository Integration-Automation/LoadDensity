from je_load_density.gui.language_wrapper.english import english_word_dict
from je_load_density.gui.language_wrapper.traditional_chinese import traditional_chinese_word_dict
from je_load_density.utils.logging.loggin_instance import load_density_logger



class LanguageWrapper(object):

    def __init__(
            self
    ):
        load_density_logger.info("Init LanguageWrapper")
        self.language: str = "English"
        self.choose_language_dict = {
            "English": english_word_dict,
            "Traditional_Chinese": traditional_chinese_word_dict
        }
        self.language_word_dict: dict = self.choose_language_dict.get(self.language)

    def reset_language(self, language) -> None:
        load_density_logger.info(f"LanguageWrapper reset_language language: {language}")
        if language in [
            "English",
            "Traditional_Chinese"
        ]:
            self.language = language
            self.language_word_dict = self.choose_language_dict.get(self.language)


language_wrapper = LanguageWrapper()
