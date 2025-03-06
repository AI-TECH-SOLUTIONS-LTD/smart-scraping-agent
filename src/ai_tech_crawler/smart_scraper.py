"""
SmartScraper Module
"""
import logging
import json
from typing import Optional, Any
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.output_parsers.format_instructions import JSON_FORMAT_INSTRUCTIONS
from langchain_core.exceptions import OutputParserException

from ai_tech_crawler.llm_friendly_loader import LLMFriendlyWebLoader
from ai_tech_crawler.prompt_factory import *
from ai_tech_crawler.custom_json_parser import json_parser



class SmartScraperAgent:
    def __init__(
            self,
            prompt: str,
            source: str,
            config: dict,
            schema: Optional[BaseModel | Any] = None
            ):
        if config.get("llm").get("temperature") is None:
            config["llm"]["temperature"] = 0

        self.prompt = prompt
        self.source = source
        self.config = config
        self.schema = schema
        config["llm"]["max_retries"] = self.config.get('max_retries') or 5
        self.llm = self._create_llm(config['llm'])

        self.verbose = False if config is None else config.get("verbose", False)
        self.headless = True if self.config is None else config.get("headless", True)
        self.user_agent = self.config.get("user_agent")
        self.loader_kwargs = self.config.get("loader_kwargs", {})
        self.cache_path = self.config.get("cache_path", False)
        self.browser_base = self.config.get("browser_base")
        self.scrape_do = self.config.get("scrape_do")
        
        self.content_type = 'advanced_markdown'

    def get_llm_provider(self, llm_provider):
        match llm_provider:
            case "openai":
                try:
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI
                except ImportError as e:
                    msg = (
                        "Unable to import from `langchain_openai`."
                        "Please install langchain-openai with "
                        "`pip install -U langchain-openai`."
                    )
                    raise ImportError(msg) from e
                
            case "ollama":
                try:
                    from langchain_ollama import ChatOllama
                    return ChatOllama
                except ImportError as e:
                    msg = (
                        "Unable to import from `langchain_ollama`."
                        "Please install langchain-ollama with "
                        "`pip install -U langchain-ollama`."
                    )
                    raise ImportError(msg) from e
            case "groq":
                try:
                    from langchain_groq import ChatGroq
                    return ChatGroq
                except ImportError as e:
                    msg = (
                        "Unable to import from `langchain_groq`."
                        "Please install langchain-groq with "
                        "`pip install -U langchain-groq`."
                    )
                    raise ImportError(msg) from e
                

    def _create_llm(self, llm_config):
        llm_defaults = {"temperature": 0, "streaming": False}
        llm_params = llm_defaults | llm_config

        if "/" in llm_params["model"]:
            split_model_provider = llm_params["model"].split("/", 1)
            llm_provider = split_model_provider[0]
            llm_params['model'] = split_model_provider[1]
        else:
            msg = ('Please specify the model provider and model name `model: <llm_provider/model_name>` in the llm configuration')
            raise ImportError(msg)
        return self.get_llm_provider(llm_provider)(**llm_params)
    
    def scrape_and_split_content(self):
        loader = LLMFriendlyWebLoader(
                                        urls=[self.source,],
                                        headless=self.headless,
                                        user_agent=self.user_agent,
                                        content_type=self.content_type
                                    )
        return loader.load_and_extract_split()
    
    def get_markdown(self):
        loader = LLMFriendlyWebLoader(
                                        urls=[self.source,],
                                        headless=self.headless,
                                        user_agent=self.user_agent,
                                        content_type='basic_markdown'
                                    )
        return loader.load()
    
    def load_indepth_and_split(self, depth: int=1):
        loader = LLMFriendlyWebLoader(
                                        urls=[self.source,],
                                        headless=self.headless,
                                        user_agent=self.user_agent,
                                        content_type='basic_markdown'
                                    )
        
        return loader.load_indepth(depth=depth)
    
    def set_format_instruction(self):
        if self.schema:
            try:
                is_schema_validated = issubclass(self.schema, BaseModel)
            except Exception as e:
                logging.info('\n❗ Pease provide a valid `pydantic` schema which is a subclass of `BaseModel` for better results.\n')
                is_schema_validated = False

            if is_schema_validated:
                output_parser = JsonOutputParser(pydantic_object=self.schema)
                format_instructions = output_parser.get_format_instructions()
                # output_parser = JsonOutputParser()
            else:
                format_instructions = JSON_FORMAT_INSTRUCTIONS.format(**{"schema": self.schema})
                output_parser = JsonOutputParser()
        else:
            logging.info('\n⛔ Pease provide a valid `pydantic` schema which is a subclass of `BaseModel` for better results.\n')
            format_instructions = "Follow the user question to generate a valid JSON output and finally wrap the result in `json` tag"
            output_parser = JsonOutputParser()

        self.output_parser = output_parser
        self.format_instructions = format_instructions

    def get_extracted_chunks(self,):
        self.set_format_instruction()
        if (additional_info := self.config.get("additional_info")):
            template_no_chunks_prompt = additional_info + TEMPLATE_NO_CHUNKS_MD
            template_chunks_prompt = additional_info + TEMPLATE_CHUNKS_MD
        else:
            template_no_chunks_prompt = TEMPLATE_NO_CHUNKS_MD
            template_chunks_prompt = TEMPLATE_CHUNKS_MD


        docs = self.scrape_and_split_content()
        current_page_doc = docs[0]
        chunks = current_page_doc.get('chunks')
        metadata = current_page_doc.get('metadata')

        max_retries: int = self.config.get('max_retries') or 3
        trial = 1

        while (trial <= max_retries):
            results = []
            if len(chunks) == 1:
                # chunk = chunks[0]
                # prompt = PromptTemplate(
                #     template = template_no_chunks_prompt,
                #     input_variables=["context", "base_url"],
                #     partial_variables= {"format_instructions": self.format_instructions, "question": self.prompt}
                # )

                # chain = prompt | self.llm | self.output_parser
                # answer = chain.invoke(chunk)
                # if answer and list(answer.values()):
                #     results = answer, metadata
                # else:
                self.content_type = "hybrid_markdown"
                trial += 1
                logging.info('\nRetrying ... .. .\n')

            else:
                extract_prompt = PromptTemplate(
                    template = template_chunks_prompt,
                    input_variables=["context", "base_url"],
                    partial_variables= {"format_instructions": self.format_instructions, "question": self.prompt}
                )
                extract_chain = extract_prompt | self.llm | json_parser

                logging.info('\n🗃️ 🎫 Extracting data from the chunks ... .. .\n')
                if 'openai' in self.config.get('llm', {}).get('model'):
                    batch_results = extract_chain.batch(
                                                            inputs=chunks,
                                                            return_exceptions = False
                                                        )
                else:
                    batch_results = []
                    for idx, chunk in enumerate(chunks):
                        try:
                            answer = extract_chain.invoke(chunk)
                            batch_results.append(answer)
                            logging.info(f'[Result] :: Chunk {idx + 1} :\n{answer}\n\n')
                        except Exception as e:
                            batch_results.append(None)
                            logging.info(f'[Error] :: Chunk {idx + 1} :\n{e.__str__()}\n\n')
                results = batch_results
                # if self.config.get('verbose'):
                #     logging.info(f'\nMetadata ::\n{metadata}\n\nExtracted results ::\n{json.dumps(results, indent=4) if isinstance(results, list) else results}\n\n\n')
            return results, metadata
    
    def get_answer(self,):
        if (additional_info := self.config.get("additional_info")):
            template_merge_prompt = additional_info + TEMPLATE_MERGE_MD
        else:
            template_merge_prompt = TEMPLATE_MERGE_MD

        max_retries: int = self.config.get('max_retries') or 3
        trial = 1

        while (trial <= max_retries):
            batch_results, metadata = self.get_extracted_chunks()
            base_url = metadata.get('base_url')

            logging.info('\n🗂️ Merging Results ... .. .\n')
            merge_prompt = PromptTemplate(
                template = template_merge_prompt,
                input_variables=["context", "base_url"],
                partial_variables= {"format_instructions": self.format_instructions, "question": self.prompt}
            )
            merge_chain = merge_prompt | self.llm | json_parser
            answer = merge_chain.invoke({"context": batch_results, "base_url": base_url})
                
            if answer:
                return answer
            else:
                self.content_type = "hybrid_markdown"
                trial += 1
                logging.info('\nRetrying ... .. .\n')
                    
        else:
            raise TimeoutError("\nMax retries completed.\n")

    def execute(self):
        # answer = self.get_answer()
        try:
            answer = self.get_answer()
        except Exception as e:
            error = f"Error :: {e.__str__()}"
            logging.error(f'--{error}')
            answer = error

        return answer
    
    def run(self):
        # answer = self.get_answer()
        try:
            answer = self.get_answer()
        except Exception as e:
            error = f"Error :: {e.__str__()}"
            logging.error(f'--{error}')
            answer = error

        return answer

        