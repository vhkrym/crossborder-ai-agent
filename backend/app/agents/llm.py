from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.config import ROOT

class LLMSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file=ROOT/'.env',extra='ignore')
    llm_base_url: str = Field(min_length=1)
    llm_api_key: SecretStr = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    llm_timeout: int=Field(default=30,ge=1,le=120)
    llm_max_retries: int=Field(default=1,ge=0,le=2)

def create_llm(settings=None):
    from langchain_openai import ChatOpenAI
    s=settings or LLMSettings()
    return ChatOpenAI(base_url=s.llm_base_url,api_key=s.llm_api_key.get_secret_value(),model=s.llm_model,default_headers={'Accept-Encoding':'identity'},timeout=s.llm_timeout,max_retries=s.llm_max_retries)

def ask_json(llm, schema, system, payload):
    import json
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        response=llm.invoke([SystemMessage(content=system+' Return only valid JSON matching: '+json.dumps(schema.model_json_schema())),HumanMessage(content=json.dumps(payload,ensure_ascii=False,default=str))])
    except TimeoutError as exc: raise ValueError('llm_timeout') from exc
    except Exception as exc:
        code='llm_timeout' if type(exc).__name__=='APITimeoutError' else 'llm_api_error'
        raise ValueError(code) from exc
    try:
        return schema.model_validate_json(response.content)
    except Exception as exc: raise ValueError('llm_invalid_json') from exc
