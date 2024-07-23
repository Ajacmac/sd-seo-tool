'''
    This module contains jobs to be queued up as part of a product offering
    for a given client.

    The jobs are composed of a series of prompts that operate on the same data.
    A job has a set of discrete inputs, a set of discrete outputs, but maybe
    do complex operations on the data in between.

    FIXME: Figure out how to handle a job invoker specifying the model to use
        - This may need to be specifiable as either a single model for the 
        entire job, or a model for each prompt, a model for prompts 1-3, and 
        a different model for prompts 4-6, etc.
    
    FIXME: Get comments on this from sonnet
    
    Do jobs need to be able to break down into other jobs?
        - How complex ought individual jobs be?

    What's a good example of a typical job?
        - Queueing up automated research?
        - Generating landing page copy and demo html with a given colour theme?
        - Generating a FAQ page?
        - Generating a blog post?
        - Generating a service page?
        - Generating a product page?
        - Determining what pages are needed for a given client?
        - SEO keyword research phases probably deserve their own jobs
    
    Anatomy of a typical job:
        - Analyze input data and how it relates to the stock description in the job itself
        - Take that analysis and iterate on it a couple times
        - Use the final, iterated analysis to generate specific guidelines for each step in the job
        - Taking all of that as input, go through the steps in that specific job
    
    Does having this much prior analysis justify coding a kind of "job runner" that takes an array
    of prompt strings with their I/O variables (similar to HDL?) and then go through it all?
        - inputs must pre-exist
        - outputs can be new or can overwrite/append/prepend existing values
        - job function args would be variables available to be inputs for these prompt definitions
        - maybe jobs create an object that holds all of these inputs and outputs?
            - that would let me just output all of the outputs at the end of the job
            - this means it'd be easier to store the job record in a database
        - { 
            "prompt": "string", 
            "inputs": { 
                "input1": "type", 
                "input2": "type" 
            }, 
            "outputs": { 
                "output1": "type", 
                "output2": "type" 
            }
        }
        
'''
import logging
import sys
from typing import Any, Dict, List, Callable
from datetime import datetime
import json
import src.lm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# JobContext and related functions (from previous implementation)
def create_job_context(**initial_inputs: Any) -> Dict[str, Any]:
    return {
        "data": initial_inputs,
        "created_at": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat()
    }

def update_job_context(context: Dict[str, Any], updates: Dict[str, Any]) -> None:
    context["data"].update(updates)
    context["last_modified"] = datetime.now().isoformat()

def get_job_context_value(context: Dict[str, Any], key: str, default: Any = None) -> Any:
    return context["data"].get(key, default)

PromptFunction = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]

def run_job(job_name: str, prompts: List[PromptFunction], initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
    context = create_job_context(**initial_inputs)
    logger.info(f"Starting job: {job_name}")
    
    for i, prompt_func in enumerate(prompts):
        try:
            logger.info(f"Running prompt {i+1}/{len(prompts)}: {prompt_func.__name__}")
            result = prompt_func(context["data"], {})
            update_job_context(context, result)
        except Exception as e:
            logger.error(f"Error in prompt {i+1}/{len(prompts)} of job '{job_name}': {str(e)}", exc_info=True)
            break
    
    logger.info(f"Job completed: {job_name}")
    return context

# Prompt functions for blog post generation
def generate_outline(inputs: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    prompt = json.dumps({
        "task": "outline",
        "topic": inputs["topic"],
        "research": inputs["research"],
        "instruction": "Create an outline for a blog post based on the given topic and research."
    })
    outline = src.lm.llama3_70b(prompt)
    return {"outline": outline}

def write_introduction(inputs: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    prompt = json.dumps({
        "task": "write_introduction",
        "topic": inputs["topic"],
        "outline": inputs["outline"],
        "instruction": "Write an engaging introduction for a blog post based on the given topic and outline."
    })
    introduction = src.lm.llama3_70b(prompt)
    return {"introduction": introduction}

def write_main_content(inputs: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    prompt = json.dumps({
        "task": "write_main_content",
        "topic": inputs["topic"],
        "outline": inputs["outline"],
        "introduction": inputs["introduction"],
        "instruction": "Write the main content for a blog post based on the given topic, outline, and introduction."
    })
    main_content = src.lm.llama3_70b(prompt)
    return {"main_content": main_content}

def write_conclusion(inputs: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    prompt = json.dumps({
        "task": "write_conclusion",
        "topic": inputs["topic"],
        "main_content": inputs["main_content"],
        "instruction": "Write a conclusion for a blog post based on the given topic and main content."
    })
    conclusion = src.lm.llama3_70b(prompt)
    return {"conclusion": conclusion}

def format_blog_post(inputs: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    prompt = json.dumps({
        "task": "format_blog_post",
        "title": f"Blog Post: {inputs['topic']}",
        "introduction": inputs["introduction"],
        "main_content": inputs["main_content"],
        "conclusion": inputs["conclusion"],
        "instruction": "Format the given components into a complete blog post."
    })
    formatted_post = src.lm.llama3_70b(prompt)
    return {"formatted_post": formatted_post}

def test():
    job_prompts = [
        generate_outline,
        write_introduction,
        write_main_content,
        write_conclusion,
        format_blog_post
    ]
    initial_inputs = {"topic": "The Impact of Artificial Intelligence on Modern Healthcare"}
    
    result = run_job("Generate Blog Post", job_prompts, initial_inputs)
    
    logger.info("Job Completion Summary:")
    for key, value in result["data"].items():
        if key == "formatted_post":
            logger.info(f"\n{value}")
        else:
            logger.info(f"{key}: {value[:50]}...")
    
    logger.info(f"Job started at: {result['created_at']}")
    logger.info(f"Job completed at: {result['last_modified']}")