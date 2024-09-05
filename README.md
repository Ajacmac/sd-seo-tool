# SEO Automation Tool

## Running the tool

docker build . -t seo-tool

docker run -v $(pwd)/volume:/volume seo-tool

docker rm $(docker ps -lq) && docker rmi $(docker images -q | head -n 1)

## Rough Stages in Pipeline

FIXME: get example inputs and outputs for each of these

- Keyword research
- Keyword clustering
- Keyword mapping
- Website structure (sitemap: what pages should be on the site and how they should be linked)
- Writing page content

FIXME: remember to stop dropping the db tables when the logic is confirmed to work



- Keyword research
	- all of the steps you go through in this process
		- clusters[ [keywords], [keywords], [keywords] ] = cluster_keywords(list of main services, client provided keywords)
		- more_seed_keywords = request_more_keywords_from_model(clusters)
		- best_seed_keywords = remove_junk(more_seed_keywords)
		- long_keyword_list = google_keyword_planner_api(best_seed_keywords)
		- high_volume_long_list = remove_keywords_with_less_than_ten_searches(long_keyword_list)
		- negative_keywords = ask_model_which_are_negative(high_volume_long_list)
		- no_negative_list = remove_negatives(high_volume_long_list, negative_keywords)
		- relevant_only = remove_irrelevant_keywords(no_negative_list)
		- reclustered = recluster_keywords(relevant_only)
	- all of the data you need to start keyword research
		- list of main services
		- client provided seed keywords
		- 
	- everything that the keyword research produces that then gets used later
- Keyword mapping (clustering iteratively around a better and better set of potential pages to write)
  - take individual keywords, look at pages in serp for keyword, and identify page intent for each
  - ensure all keywords in a cluster have the same intent, moving them to a different cluster if they don't
- Website structure (sitemap: what pages should be on the site and how they should be linked)
  - Website structure is *almost* dictated by the keyword mapping
- Writing page content
  - figure out what goes on each page
  - Research
    - Find FAQ questions (from google, etc.)


## Overview

Automates SEO tasks like keyword research, content generation, etc.

FIXME: some of these list items aren't in order (I got them down as Roman said them)

Steps
Intake form -> seed keywords 
    - The form mentions what they want to rank for
    - Look at their products/services (product/service names are useful seed keywords)

-> keyword research
    - Get big keyword list from API
    - Identify junk keywords and remove them (very obviously irrelevant)
    - Identify and remove negative keywords
    - Find related keywords
    - Filter out low search volume
    - Find more irrelevant keywords and remove them
    - Group keywords by intent (I have 4 intent types, but I should check if there are more)
    - Group keywords around product/service pages
      - There can also be subpages that focus on a niche within a broader service
    - Verify that your clusters target the same intents that competitors in SERP target
    - Find keyword synonyms and autocomplete suggestions
    - Use "People also ask" and "Searches related to" to find more keywords
      - Also good for FAQ pages
    - Keyword gap tool? RankTracker?
      - Find keywords that competitors are ranking for but you aren't
      - Compare specific product/service pages between our client and competitors

-> content generation -> content optimization -> content publishing -> content promotion


Misc. Ideas

- TF-IDF analysis
- Other NLP algorithms?
- Other algorithms?
- Research NLP algorithms for SEO

- Analyze competitor pages to see what psychological profile they're targeting
  - Big 5 Factor personality traits
  - Hexaco?
  - The content and/or typical buyer can likely be modelled pretty well with these
  - Have model determine why competitors are targeting that profile
  - Identify whether there may be room for improvement in targeting a (subtly?) different profile

## API Providers

Language Models
- Groq
- OpenAI
- Claude

Other AI
- Sentiment Analysis
- What other NLP stuff uses small models like BERT?

SEO
- Google Ad Keyword Planner API
- Georanker API
- 

Search
- Tavily?
- Bing API?
- DuckDuckGo API?
- Brave Search?


## ToDo

FIXME: Take prompts 1&2 from SOP - Write Content For Service Page and implement them in the tool

FIXME: Make sure the color palette extraction is included in the pipeline now that it's working

TODO: Figure out how to specify the individual prompts in the chains
    - Goals should be to maximize the ease and clarity of both specifying them and using them
    - Try to make it beautiful. You'll be working with this a lot.
    - This is also basically what langchain does, so it's a perfect opportunity to dig my teeth into designing that kind of library

TODO: Check if there is google my business profile and grab reviews if there is

TODO: Take each prompt for generating content and have sonnet generate a checklist for each prompt
  - Each check in the checklist will be handed to a model with the text it's associated with and the model will return a score
  - Poor scores will que a human to review the content and/or the model to rewrite the content
  - Take the entire checklist, pass is to sonnet, and have sonnet determine which should also be included in the original prompt
    - Maybe this ends up being 100% of requirements being in both the prompt and the checklist, but that's fine if it is

  TODO: What can I do to provide detailed analysis of various pieces of text to then be able to steer the model for tone of voice in a detailed and reliable way?
    - How can I detect corporate language?
    - How could I frame my request to the model in such a way that it naturally avoids corporate langauge?
  
  TODO: There's probably a way to take the info from the onboarding form, plus their current website (if they have one)
    and generate a theme or pseudo-theme for them to steer the models writing away from corporate language
    - Big companies don't use themes because themes will appeal to some people and push others away
    - Big companies want to appeal to everyone
    - Small companies want to appeal more strongly to a narrower group of people
    - Using a theme should make the output more similar to non-corporate text in the training data of the model so should help avoid corporate language in the output as a consequence
  
  TODO: Idea for onboarding form data -> page generation
    - embedding model embeds all of the data from the onboarding form
      - each question gets checked for length
        - short enough question text & answer text pairs are embedded together
        - longer ones get chunked and embedded (probably q & a1, ... , q & aN)
    - cosine similarity and other similarity scores get used to decide which data is needed
        for which pages and page sections, so we can keep the text passed to the model shorter
        in case all the needed text doesn't fit
  
  TODO: Automatic page planning and keyword:page mapping
    - Acquire massive list of candidate keywords (10k or more is great)
    - Rank them by similarity to primary offerings from client
    - Cluster the most similar keywords automatically using hierarchical clustering or similar
    - Have LM decide what intent and page type each cluster would be best suited for
    - Add the search volume data and determine which pages should actually get made


## Weird autocompletes from copilot

- **Keyword Research**
  - Find keywords with high search volume and low competition
  - Find keywords that competitors are ranking for
  - Find keywords that competitors are not ranking for
  - Find keywords that competitors are not targeting
  - ~ ranking for but have high search volume
  - ~ targeting but have high search volume
  - ~ ranking for but have high search volume and low competition
  - ~ targeting but have high search volume and low competition
  - ~ ranking for but have high search volume and low competition and are related to a specific topic
  - ~ targeting but have high search volume and low competition and are related to a specific topic
  - ~ ranking for but have high search volume and low competition and are related to a specific topic and have a specific intent
  - ~ targeting but have high search volume and low competition and are related to a specific topic and have a specific intent
  - ~ ranking for but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language
  - ~ targeting but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language
  - ~ ranking for but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language and are in a specific country
  - ~ targeting but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language and are in a specific country
  - ~ ranking for but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language and are in a specific country and are in a specific region
  - ~ targeting but have high search volume and low competition and are related to a specific topic and have a specific intent and are in a specific language and are in a specific country and are in a specific region