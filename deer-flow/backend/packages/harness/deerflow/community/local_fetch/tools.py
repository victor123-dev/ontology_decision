"""
Local Web Fetch Tool - Completely offline, no API key required.

This module implements a fully local web fetch mechanism that:
1. Uses httpx to fetch web pages directly
2. Extracts main content using Readability (local processing)
3. Converts HTML to Markdown using markdownify
4. No external API dependencies or API keys needed
"""

import logging
from typing import Optional

import httpx
from langchain.tools import tool

from deerflow.config import get_app_config
from deerflow.utils.readability import ReadabilityExtractor

logger = logging.getLogger(__name__)

readability_extractor = ReadabilityExtractor()

# Default configuration
DEFAULT_TIMEOUT = 30  # seconds (increased from 15 for better reliability)
DEFAULT_MAX_CHARS = 4096
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_MAX_REDIRECTS = 5


def _build_headers(custom_user_agent: Optional[str] = None) -> dict:
    """Build HTTP headers for the request."""
    return {
        "User-Agent": custom_user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        # httpx handles decompression automatically, don't specify Accept-Encoding
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


async def _fetch_html(url: str, timeout: int, user_agent: Optional[str] = None) -> str:
    """
    Fetch HTML content from a URL using httpx.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        user_agent: Custom User-Agent string (optional)
    
    Returns:
        HTML content as string
    
    Raises:
        Exception: If the request fails
    """
    headers = _build_headers(user_agent)
    
    async with httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=DEFAULT_MAX_REDIRECTS,
        timeout=timeout,
        verify=True
    ) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response encoding: {response.encoding}")
            logger.debug(f"Content-Type: {response.headers.get('content-type')}")
            logger.debug(f"Content-Encoding: {response.headers.get('content-encoding')}")
            
            # httpx automatically decompresses gzip/br/deflate
            # Use response.text which handles decoding automatically
            # If that fails, try manual decoding with apparent_encoding
            try:
                html_content = response.text
                logger.debug(f"Using response.text, length: {len(html_content)}")
            except Exception as decode_error:
                logger.warning(f"response.text failed: {decode_error}, trying manual decoding")
                # Fallback to manual decoding
                if response.apparent_encoding:
                    html_content = response.content.decode(response.apparent_encoding, errors='replace')
                    logger.debug(f"Using apparent_encoding: {response.apparent_encoding}")
                else:
                    html_content = response.content.decode('utf-8', errors='replace')
                    logger.debug("Using utf-8 fallback")
            
            # Validate that we got actual HTML content
            # Check if content looks like binary/garbage
            if not html_content or len(html_content.strip()) == 0:
                raise Exception("Empty response")
            
            # Quick check: if it looks like binary data, reject it
            # Valid HTML should have printable ASCII characters
            sample = html_content[:500]
            printable_ratio = sum(1 for c in sample if c.isprintable() or c in '\n\r\t') / len(sample)
            if printable_ratio < 0.7:
                logger.warning(f"Response looks like binary data (printable ratio: {printable_ratio:.2f})")
                logger.warning(f"First 200 bytes of raw content: {response.content[:200]}")
                raise Exception(f"Response appears to be binary data (printable ratio: {printable_ratio:.2f})")
            
            return html_content
            
        except httpx.TimeoutException:
            error_msg = f"Request to {url} timed out after {timeout} seconds"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.TooManyRedirects:
            error_msg = f"Too many redirects for {url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} for {url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise


@tool("web_fetch", parse_docstring=True)
async def web_fetch_tool(url: str) -> str:
    """
    Fetch the contents of a web page at a given URL.
    
    This is a COMPLETELY LOCAL implementation that requires NO API KEY.
    It fetches HTML directly and extracts readable content using Readability.
    
    Only fetch EXACT URLs that have been provided directly by the user or 
    have been returned in results from the web_search and web_fetch tools.
    
    This tool can NOT access content that requires authentication, such as 
    private Google Docs or pages behind login walls.
    
    Do NOT add www. to URLs that do NOT have them.
    URLs must include the schema: https://example.com is a valid URL while 
    example.com is an invalid URL.

    Args:
        url: The URL to fetch the contents of.
    
    Returns:
        Markdown-formatted content extracted from the web page (max 4096 chars)
    """
    try:
        # Get configuration
        config = get_app_config().get_tool_config("web_fetch")
                
        timeout = DEFAULT_TIMEOUT
        max_chars = DEFAULT_MAX_CHARS
        user_agent = None
                
        if config is not None:
            timeout = config.model_extra.get("timeout", DEFAULT_TIMEOUT)
            max_chars = config.model_extra.get("max_chars", DEFAULT_MAX_CHARS)
            user_agent = config.model_extra.get("user_agent")
                
        logger.info(f"Local web fetch: {url} (timeout={timeout}s)")
                
        # Step 1: Fetch HTML content
        html_content = await _fetch_html(url, timeout, user_agent)
                
        if not html_content or not html_content.strip():
            return "Error: Empty response from server"
                
        # Check if content looks like valid HTML
        if not ('<html' in html_content or '<!DOCTYPE' in html_content or '<head' in html_content or '<body' in html_content):
            logger.warning(f"Response doesn't look like HTML (first 200 chars): {html_content[:200]}")
            return f"Error: Response doesn't appear to be HTML. Got: {html_content[:200]}..."
                
        # Step 2: Extract main content using Readability
        article = readability_extractor.extract_article(html_content)
                
        # Step 3: Convert to Markdown
        markdown_content = article.to_markdown()
                
        # Step 4: Truncate to max_chars
        if len(markdown_content) > max_chars:
            markdown_content = markdown_content[:max_chars] + "\n\n... [Content truncated]"
                
        logger.info(f"Successfully fetched and extracted content ({len(markdown_content)} chars)")
                
        return markdown_content
                
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
