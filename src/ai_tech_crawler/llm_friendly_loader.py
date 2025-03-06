"""
This module is used for scraping, loading and preprocessing data in a format that is 
compatible with Large Language Models (LLMs).

"""


import os
import logging
import re
from urllib.parse import urlparse
import asyncio
from datetime import datetime

from typing import List, Optional, Dict, AsyncIterator, Iterator, Any, Union

from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader
from langchain_text_splitters import TextSplitter

from ai_tech_crawler.utils import store_web_reader_contents, count_tokens


class LLMFriendlyWebLoader(BaseLoader):
    """
    Scrape HTML pages from URLs using a
    headless instance of the Chromium.

    `Author`: Rohan Dhanraj Yadav
    `Email`: rohan.aigroup@gmail.com
    """

    def __init__(
        self,
        *,
        urls: List[str] | str=[],
        headless: bool = True,
        user_agent: Optional[str] = None,
        content_type: Optional[str] = None
    ):
        """
        Initialize the loader with a list of URL paths.

        Args:
            urls: A list of URLs to scrape content from.
            headless: Whether to run browser in headless mode.
            user_agent: The user agent to use for the browser
            content_type: The content type of scraped content. Any of `html`, `basic_markdown`, `advanced_markdown`. Defaults to `advanced_markdown`.

        Raises:
            ImportError: If the required 'playwright' package is not installed.
        """
        if isinstance(urls, list):
            self.urls = urls
        elif isinstance(urls, str):
            self.urls = [urls,]
        else:
            raise ValueError(
                "The `urls` parameter must be "
                "a string containing an HTTP URL or "
                "a list of strings containing HTTP URLs."
                )
        self.headless = headless
        self.user_agent = user_agent or os.getenv('USER_AGENT')
        self.content_type = content_type or 'basic_markdown'
        
        try:
            import playwright  # noqa: F401
        except ImportError:
            raise ImportError(
                "playwright is required for GenericWebScraper. "
                "Please install it with `pip install playwright`."
            )
        
    async def ascrape_playwright(
                                    self,
                                    url: str,
                                    headers: Dict[str, str] = {}
                                ) -> str:
        """
        Asynchronously scrape the content of a given URL using Playwright's async API.

        Args:
            url (str): The URL to scrape.

        Returns:
            str: The scraped HTML content or an error message if an exception occurs.

        """
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
        
        result = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                page = await browser.new_page(
                    user_agent=self.user_agent,
                    extra_http_headers=headers
                )
                await stealth_async(page)
                await page.goto(url)
                logging.info("\n✅ Successfully loaded requested page.\n")

                # Auto-scroll to the bottom of the page
                # Function to append content while scrolling
                async def append_content():
                    nonlocal result
                    result += await page.content()  # Capture the initial content
                    last_height = await page.evaluate("document.body.scrollHeight")
                    while True:
                        # Scroll down by a small amount
                        await page.evaluate("window.scrollBy(0, 500);")
                        await page.wait_for_timeout(500)  # Wait for content to load

                        # Capture the updated content
                        new_content = await page.content()
                        if new_content and (new_content not in result):  # Append only if new content is loaded
                            result += new_content

                        # Check if we've reached the bottom of the page
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            break  # Exit if no more content is loaded
                        last_height = new_height

                # Append content while scrolling
                await append_content()
                logging.info("\n🔄 Finished auto-scrolling to the bottom of the page.\n")

                # Get the fully loaded HTML content
                result = await page.content()
                logging.info("\n✨ Content scraped successfully.\n")

            except Exception as e:
                result = f"🚧 Scraping Error :: {e.__str__()}"
                logging.error(f"\n{result}\n")

            logging.info("\n🔒 Closing Scraping session.\n")
            await browser.close()
        return result
    
    def get_web_html(self, url: str, headers: Dict[str, str] = {}):
        logging.info(f"\n🔍 Starting a scraper request for {url} ... .. .\n")
        return asyncio.run(self.ascrape_playwright(url, headers))
    
    def get_advanced_markdown(self, url: str, headers: Dict[str, str] = {}):
        logging.info(f"\n🔍 Starting a jina reader request to scrape {url} ... .. .\n")
        headers = (
                    headers
                    | {
                        'x-timeout': '60'
                      } 
                  )
        
        link = f'https://r.jina.ai/{url}'

        return asyncio.run(self.ascrape_playwright(link, headers))
    
    def get_basic_markdown(
                            self,
                            url: str,
                            headers: Dict[str, str] = {},
                            strip: Optional[Union[str, List[str]]] = None,
                            convert: Optional[Union[str, List[str]]] = None,
                            autolinks: bool = True,
                            heading_style: str = "ATX",
                            **kwargs: Any
                        ):
        try:
            from markdownify import markdownify as md
        except ImportError:
            raise ImportError(
                """markdownify package not found, please 
                install it with `pip install markdownify`"""
            )
        logging.info(f"\n🔍 Starting a crawler request to scrape {url} ... .. .\n")

        parsed_url = urlparse(url=url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        # markdown_content = (
        #                         md(
        #                             html=self.get_web_html(url=url, headers=headers),
        #                             strip=strip,
        #                             convert=convert,
        #                             autolinks=autolinks,
        #                             heading_style=heading_style,
        #                             **kwargs,
        #                           )
        #                         .replace("\xa0", " ")
        #                         .strip()
        #                     )
        html_text = self.get_web_html(url=url, headers=headers)
        cleaned_html_content = re.sub(r'<(meta|script|style|noscript)[^>]*>.*?</\1>', '', html_text, flags=re.DOTALL)

        markdown_content = md(cleaned_html_content)

        titles = re.findall(r'^#\s([^\n#]+)', markdown_content, re.MULTILINE)
        if titles:
            title = titles[0]
            markdown_content = markdown_content.replace(f'# {title}', '')
            cleaned_title = f"Title :: {title.replace('# ', '').replace('\n', '')} \n{'='*(len(title) + 10)}"
        else:
            cleaned_title = ''

        markdown_content = self.format_and_add_base_url(markdown_content, base_url)

        cleaned_markdown = re.sub(r"\n\s*\n", "\n\n", markdown_content)
        
        result = f"{cleaned_title}\n\nSource URL :: {url}\n\nMarkdown Content:: \n{'-'*20}\n```\n{cleaned_markdown}\n```"

        return result
    
    @staticmethod
    def format_and_add_base_url(markdown_text, base_url):
        """
        Formats Markdown text by appending a base URL to relative links and image links,
        and ensures proper formatting of nested links.

        Args:
            markdown_text (str): The Markdown text to format.
            base_url (str): The base URL to prepend to relative links.

        Returns:
            str: The reformatted Markdown text with updated links and proper formatting.
        """
        # Regex pattern to match Markdown links (including nested and image links)
        pattern = r'(!?\[([^\]]*)\]\(([^\)]+)\))(?:\(([^\)]+)\))?'

        def replace_link(match):
            full_match = match.group(1)
            text_part = match.group(2)
            url = match.group(3)
            nested_link = match.group(4)

            # Skip links that are already absolute or not valid for base URL appending
            if url.startswith(("mailto:", "http://", "https://", "data:image", "/data:image", "tel:")):
                return full_match

            # Prepend base URL to relative links
            if url.startswith("/"):
                url = f"{base_url}{url}"
            elif url.startswith("./"):
                url = f"{base_url}{url[1:]}"
            else:
                url = f"{base_url}/{url}"

            # Handle nested links (e.g., [![alt text](image_url)](link_url))
            if nested_link:
                if not nested_link.startswith(("mailto:", "http://", "https://", "data:image", "/data:image", "tel:")):
                    if nested_link.startswith("/"):
                        nested_link = f"{base_url}{nested_link}"
                    elif nested_link.startswith("./"):
                        nested_link = f"{base_url}{nested_link[1:]}"
                    else:
                        nested_link = f"{base_url}/{nested_link}"
                return f"[![{text_part}]({url})]({nested_link})"

            # Regular links or image links
            if not text_part:
                return f"![]({url})"
            return f"[{text_part}]({url})"

        # Replace all links in the Markdown text
        modified_text = re.sub(pattern, replace_link, markdown_text)

        # Ensure proper formatting of links and nested elements
        modified_text = re.sub(r'\)([^\n\[])', r')\n\1', modified_text)  # Newline after links
        modified_text = re.sub(r'(\S)(\[!\[)', r'\1\n\2', modified_text)  # Newline for nested Markdown
        modified_text = re.sub(r'(\[!\[[^\]]*\]\([^\)]+\))\s+([^\]]+)\]\(([^\)]+)\)', r'[\1 \2](\3)', modified_text)  # Handle nested links

        # Ensure newlines after major sections
        modified_text = re.sub(r'(\]\(.*?\))(\S)', r'\1\n\2', modified_text)

        return modified_text

    
    @staticmethod
    def extract_urls(markdown_text):
        return re.findall(
            r'(?<!\!)\[[^\]]+\]\((?!mailto:)([^\)]+)\)|https?://[^\s\)]+',
            markdown_text
            )

    def get_hybrid_markdown(self, url: str, headers: Dict[str, str] = {}):
        logging.info(f"\n🔍 Starting a hybrid scraping request for {url} ... .. .\n")
        return f"Basic Markdown ::\n{'='*20}\n\n{self.get_basic_markdown(url, headers)}{'\n'*5}{'*'*100}\n{'End of Basic Markdown' : ^100}\n{'*'*100}{'\n'*5}Advanced Markdown ::\n{'='*20}\n\n{self.get_advanced_markdown(url, headers)}"
    
    def get_content(self, url):
        match self.content_type:
            case 'html':
                return self.get_web_html(url)
            case 'basic_markdown':
                return  self.get_basic_markdown(url)
            case 'advanced_markdown':
                return self.get_advanced_markdown(url)
            case 'hybrid_markdown':
                return self.get_hybrid_markdown(url)
            case _:
                return self.get_advanced_markdown(url)

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazily load text content from the provided URLs.

        This method yields Documents one at a time as they're scraped,
        instead of waiting to scrape all URLs before returning.

        Yields:
            Document: The scraped content encapsulated within a Document object.

        """
        for url in self.urls:
            parsed_url = urlparse(url=url)
            content = self.get_content(url=url)
            metadata = {
                            "base_url": f"{parsed_url.scheme}://{parsed_url.netloc}",
                            "domain": parsed_url.netloc,
                            "url_path": parsed_url.path, 
                            "source": url,
                            "created_at": datetime.now()
                        }
            yield  Document(page_content=content, metadata=metadata)

    async def alazy_load(self) -> AsyncIterator[Document]:
        """
        Asynchronously load text content from the provided URLs.

        This method leverages asyncio to initiate the scraping of all provided URLs
        simultaneously. It improves performance by utilizing concurrent asynchronous
        requests. Each Document is yielded as soon as its content is available,
        encapsulating the scraped content.

        Yields:
            Document: A Document object containing the scraped content, along with its
            source URL as metadata.
        """
        tasks = [self.get_content(url=url) for url in self.urls]
        results = await asyncio.gather(*tasks)
        for url, content in zip(self.urls, results):
            parsed_url = urlparse(url=url)
            metadata = {
                            "base_url": f"{parsed_url.scheme}://{parsed_url.netloc}",
                            "domain": parsed_url.netloc, 
                            "url_path": parsed_url.path,  
                            "source": url,
                            "created_at": datetime.now()
                        }
            yield Document(page_content=content, metadata=metadata)

    def load_and_extract_split(
        self, text_splitter: Optional[TextSplitter] = None
    ) -> list[Document | Dict[str, str | list[dict]]]:
        """Load Documents and split into chunks. Chunks are returned as Documents.

        Do not override this method. It should be considered to be deprecated!

        Args:
            text_splitter: TextSplitter instance to use for splitting documents.
              Defaults to RecursiveCharacterTextSplitter.

        Returns:
            List of Documents.
        """
        chunked_pages = []
        file_ext = 'txt'
        if text_splitter is None:
            if 'markdown' in self.content_type :
                try:
                    from langchain_text_splitters import MarkdownTextSplitter
                except ImportError as e:
                    msg = (
                        "Unable to import from langchain_text_splitters. Please specify "
                        "text_splitter or install langchain_text_splitters with "
                        "`pip install -U langchain-text-splitters`."
                    )
                    raise ImportError(msg) from e
                
                _text_splitter: TextSplitter = MarkdownTextSplitter()
                file_ext = 'md'
            else:
                try:
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                except ImportError as e:
                    msg = (
                        "Unable to import from langchain_text_splitters. Please specify "
                        "text_splitter or install langchain_text_splitters with "
                        "`pip install -U langchain-text-splitters`."
                    )
                    raise ImportError(msg) from e

                _text_splitter: TextSplitter = RecursiveCharacterTextSplitter()
      
        else:
            _text_splitter = text_splitter

        # Custom Logic
        docs = self.load()
        for doc in docs:
            chunks_out = []
            metadata = doc.metadata
            page_content = doc.page_content
            base_url = metadata.get('base_url')
            file_name = f"{metadata.get('domain')} {metadata.get("url_path")[1:].replace('/', ' ').replace('?', ' ==> ')}"
            file_name_with_ext = f"{file_name}.{file_ext}"
            metadata['file_name'] = file_name
            # store_web_reader_contents(file_name_with_ext, page_content)
            chunks = _text_splitter.split_text(page_content)
            logging.info(f'\n🔪 Splitted web content into {len(chunks)} chunks.\n')
            # logging.info(f'\nSplit Summary::\n{"-"*15}')
            for idx, chunk in enumerate(chunks):
                chunk_id = idx + 1
                # logging.info(f'Chunk # {chunk_id} :: {count_tokens(chunk)}')
                chunks_out.append(
                                    {
                                        'chunk_id': chunk_id,
                                        'base_url': base_url,
                                        'context': chunk
                                    }
                                 )
            chunked_pages.append({'metadata': metadata, 'chunks': chunks_out})
        return chunked_pages
    
    def load_and_split(self, text_splitter = None):
        if text_splitter is None:
            if 'markdown' in self.content_type :
                try:
                    from langchain_text_splitters import MarkdownTextSplitter
                except ImportError as e:
                    msg = (
                        "Unable to import from langchain_text_splitters. Please specify "
                        "text_splitter or install langchain_text_splitters with "
                        "`pip install -U langchain-text-splitters`."
                    )
                    raise ImportError(msg) from e
                
                text_splitter: TextSplitter = MarkdownTextSplitter()
        return super().load_and_split(text_splitter)

    def load_indepth(self, depth: int=1):
        all_urls = [] + self.urls
        all_splits = []
        while depth:
            logging.info(f'Level :: {depth}')
            current_splits = self.load_and_split()
            all_splits += current_splits
            if depth >= 2:
                self.urls = []
                for doc in current_splits:
                    image_extensions = (
                        '.jpg', '.jpeg', '.png', 
                        '.gif', '.bmp', '.svg',
                        '.webp', '.tiff', '.ico'
                    )
                    text = doc.page_content
                    next_urls = list(
                        filter(
                            lambda url: all(
                                [
                                    url, 
                                    not (url in all_urls or url in self.urls), 
                                    not url.lower().endswith(image_extensions),
                                    not url.startswith(("mailto:", "data:image", "/data:image", "tel:"))
                                ]
                            ),
                            set(self.extract_urls(text))
                            )
                        )
                    self.urls += next_urls

                logging.info('\n'.join(self.urls))
                all_urls += self.urls
            depth -= 1

        return all_splits
