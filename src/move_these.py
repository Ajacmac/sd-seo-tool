import json
import logging
import time

import keywords

logger = logging.getLogger(__name__)


def test_embeddings():
    """
    FIXME: refactor this and move it to the tests directory

    Tests the embedding service by bucketing a sample list of keywords
    based on similarity to a seed keyword.

    So the test with "dog" didn't return *anything* with a cosine similarity
    less than 0.25

    Try a larger search tomorrow where "dog", "dog toy", and "the best dog toys"
    are compared to all of each of their similar search keyword results.
    - Will take WAY longer to run, but hopefully I can find some worse matches
    and learn something from the data

    I also seriously need to get the memory usage down
    """

    keyword = "dog"
    search_record = keywords.db.get_similar_keyword_search(keyword, "CA")
    logger.info(f"Search record: {search_record['response_json']}")
    search_dict = json.loads(search_record["response_json"])
    logger.info(f"Search dict: {search_dict}")
    keyword_list = []
    for kw in search_dict:
        keyword_list.append(kw)
        logger.info(f"Keyword: {kw}")
    bucketed_keywords = keywords.bucket_keywords(keyword, keyword_list)

    # write the bucketed keywords to a json file
    output_file = open("/volume/bucketed_keywords.json", "w")
    json.dump(bucketed_keywords, output_file)


def test_keyword_research_for_eastern():
    """
    FIXME: refactor this and move it to the tests directory

    Ontario/Eastern Canada:
        Apple bin carrier
        Fruit bin carrier
        Vegetable bin carrier

    Michigan/Midwest US:
        Apple box shuttle
        Fruit box shuttle
        Vegetable box shuttle

    General/Nationwide:
        Apple bin trailer
        Fruit bin trailer
        Vegetable bin trailer
        Orchard bin trailer
        Bin carrier
        Bin trailer
    """

    kw_loc_pairs = [
        ["Apple bin carrier", "CA"],
        ["Fruit bin carrier", "CA"],
        ["Vegetable bin carrier", "CA"],
        ["Apple box shuttle", "US"],
        ["Fruit box shuttle", "US"],
        ["Vegetable box shuttle", "US"],
        ["Apple bin trailer", "US"],
        ["Fruit bin trailer", "US"],
        ["Vegetable bin trailer", "US"],
        ["Orchard bin trailer", "US"],
        ["Bin carrier", "US"],
        ["Bin trailer", "US"],
    ]

    {
        "company_name": "Eastern MFG",
        "company_url": "https://easternmfg.ca",
        "company_description": "Eastern Manufacturing is a manufacturer of trailers for orchards and farms.",
        "starter_keywords": [
            "Apple bin carrier",
            "Fruit bin carrier",
            "Vegetable bin carrier",
        ],
        "current_pages": [
            {
                "name": "apple_bin_trailer",
                "type": "product",
                "link": "https://easternmfg.ca/apple-bin-trailer",
                "info": "this is a trailer for orchard/apple bins that orchards use to collect and move fruit",
            },
            {
                "name": "fruit_bin_trailer",
                "type": "product",
                "link": "https://easternmfg.ca/fruit-bin-trailer",
                "info": "this is a trailer for fruit bins that orchards use to collect and move fruit",
            },
        ],
    }

    keyword_list = [kw[0] for kw in kw_loc_pairs]
    similar_kw_list = []

    """
        Structure for final_buckets:
        Dict[str: Dict[str: List[str]]]
        {
            "keyword": {
                "-1": ["similar_kw1", "similar_kw2", "similar_kw3"],
                "-0.75": ["similar_kw4", "similar_kw5", "similar_kw6"],
        }
    """
    final_buckets = {}

    for keyword in kw_loc_pairs:
        keyword.append(keywords.embedding_service.get_embedding(keyword[0]))

    # This creates a set of files named things like "bucketed_keywords_timestamp.json"
    for keyword in kw_loc_pairs:
        response = keywords.get_similar(keyword[0], keyword[1])
        if response:
            data = json.loads(response["response_json"])
            for item in data:
                similar_kw_list.append(item)

    for kw in keyword_list:
        bucketeted = keywords.bucket_keywords(kw, similar_kw_list)
        final_buckets[kw] = bucketeted

    output_file = open("/volume/bucketed_keywords.json", "w")
    json.dump(final_buckets, output_file)


def end_to_end():
    """
    FIXME: break this up into pieces and move each piece where it needs to go

    Take input from json object with all company information

    Take starter keywords and generate long list of seed keywords
    Use similarity api to get long list of candidate keywords

    Use embeddings to bucket candidate keywords based on similarity to seed keywords

    Cluster the best keywords around the different service/product pages for the client
        - Generate clusters for each page on the existing website
        - TF-IDF then cosine similarity(maybe KMeans?)

    Google doesn't provide an api, so we can determine intent by grabbing serp links +
    descriptions for each keyword, from each of duckduckgo, bing, and brave search
    (Yahoo!, Baidu, Yandex, and Ask are also options)
        - Figure out which search engines are just bing under the hood
        - does a model exist to automatically classify data by search intent?

    Generate content for each page based on the keywords and the client information

    FIXME: I need to make this more clear and concise.
    It's going to need to be refactored into a job of some sort, so it needs to be
    readable so I can safely refactor it after.

    FIXME: If I provided the model with a description of the company, could it determine
    which keyword clusters are not relevant?
    - Could it also determine which keywords inside a cluster aren't relevant?

    TODO: --- For tonight and tomorrow ---
    - LM summarizes company using scraped data from clients website + provided documents
    - LM describes each cluster of keywords
    - LM classify each keyword in a cluster as relevant or not
    - LM classify each relevant keyword by estimated search intent
        - Use SERP results to assist identifying intent
    - LM generates product/service page content based on company info, the keywords
        in the cluster, and intent
    """

    company_string = f"""Basic company profile: 
    Name: {client_data['company_name']}
    Description: {client_data['company_description']}
    Website: {client_data['company_url']}"""

    full_kw_list = []

    similar_kw_dict = {}
    total_found = 0
    for loc in client_data["locations"]:
        # results seems to be equal to client_provided_keywords list
        # why?
        results = keywords.get_similar_multi(client_provided_keywords, loc)
        similar_kw_dict[loc] = results
        logger.info(f"Keywords found: {len(results)}")
        total_found += len(results)
        for kw in results:
            full_kw_list.extend(results[kw])

    logger.info(f"full_kw_list with dupes: {len(full_kw_list)} - {full_kw_list}")

    # remove duplicates
    full_kw_list = list(set(full_kw_list))

    logger.info(f"Total keywords found: {total_found}")
    logger.info("-------------------------------")
    logger.info(f"full_kw_list w/o dupes: {len(full_kw_list)} - {full_kw_list}")
    logger.info("-------------------------------")
    logger.info(f"Similar keyword dict: {similar_kw_dict}")
    logger.info("-------------------------------")

    bucketed = {}
    for kw in client_provided_keywords:
        bucketed[kw] = embedding_service.bucket_cosine(
            kw, full_kw_list, center_type="keyword"
        )

    # Find the centroid for all seed keywords
    centroid = embedding_service.get_centroid(client_provided_keywords)

    # Bucket all keywords against centroid
    bucketed["seed centroid"] = embedding_service.bucket_cosine(
        centroid, full_kw_list, center_type="embedding"
    )

    # Find clusters within the group of all keywords
    clustered = embedding_service.hierarchical_clustering(
        full_kw_list, len(client_provided_keywords)
    )

    # bucket against page items in client_data['current_pages']
    for page in client_data["current_pages"]:
        page_string = f"Base info for a web page to be rewritten:\nname: {page['name']}\ntype: {page['type']}\nlink: {page['link']}\ninfo: {page['info']}\nbenefits: {page['benefits']}"
        bucketed[f"page-{page['name']}"] = embedding_service.bucket_cosine(
            page_string, full_kw_list, center_type="keyword"
        )

    # generate new bucket object { "page1": [], "page2": [] } with only 0.64 cosine similarity
    # or higher

    csv_buckets = json.load(open(f"{client_path}csv_bucketed_keywords.json", "r"))
    best_keywords = {}
    for page in csv_buckets:
        temp = []
        for bucket in csv_buckets[page]:
            # This threshold should be replaced with going from most relevant to least
            # and just adding more keywords until a total keyword count is reached
            # the herbicide sprayer currently gets all of 4 keywords
            # and the bin trailer gets hundreds of keywords
            if float(bucket) >= 0.69:
                temp.extend(csv_buckets[page][bucket])
        best_keywords[page] = temp

    # use hierarchical clustering to auto-cluster the most relevant keywords to each page
    # just for apple bin trailer to start
    # the number "10" is the max clusters
    # FIXME: Figure out how to get the clusters to group by intent
    # If not by intent then something else that's more useful
    # Right now the clusters being generated aren't that helpful
    # best_keywords = json.load(open(f"{client_path}best_keywords.json", "r"))
    page_clusters = embedding_service.hierarchical_clustering(
        best_keywords["apple_bin_trailer"], 10
    )

    page_clusters = json.load(
        open(f"{client_path}apple_bin_trailer_clusters.json", "r")
    )
    logger.info(f"keyword count in page clusters: {len(page_clusters)}")

    # determine what kind of page would address each cluster

    # LM classify each keyword in cluster by estimated search intent
    # - supplement with serp info for keywords
    #   - would that be a lot of data?

    # LM describes each keyword cluster

    # LM builds selected pages section by section
    service_page_sections = json.loads(
        open("/app/page_specs/service_page.json", "r").read()
    )
    start_html_section = "This is the first part of the html document. Include everything required to start an html file, like all the head imports, metadata, etc. down to the opening tag for the body.\n\n"
    end_end_section = "This is the last part of the html document. Include everything required to end an html file, like the closing tag for the body.\n\n"

    all_sections = []
    all_sections.append(start_html_section)
    all_sections.extend(service_page_sections["slim"])
    all_sections.append(end_end_section)

    logger.info(json.dumps(all_sections))
    # logger.info(service_page_sections)

    client_info = company_string + "\n\n" + json.dumps(client_data["current_pages"])
    prompt_model_response_format = """
            response_format: please output JSON with the following structure: 
            { 
                'assistant_analysis: 'write all of your analysis, thoughts, considerations, etc. here.', 
                'output': 'write your actual response to the prompt here' 
            }"""
    color_palette = palette.extract_colorhunt_palette(
        "https://colorhunt.co/palette/02152603346e6eacdae2e2b6"
    )

    # Use llama 3.1 70b on groq to decide which cluster to use for the page
    # cluster_selection_prompt = f"Here is a set of keyword clusters:\n\n{json.dumps(page_clusters, indent=4)}\n\nWhich cluster would you like to use for the following page?\n\n{client_data['current_pages'][0]}\n\n{prompt_model_response_format}\n\nFor your output just respond with the number of the cluster you want to use. Remember not to use any characters (e.g. newline) that cannot be encoded safely into JSON."
    cluster_selection_prompt = f"""Here is a set of keyword clusters:\n\n{json.dumps(page_clusters, indent=4)}\n\nFrom that list of clusters, please assemble a new list of keywords that will be used for the following page.\n\n{client_data['current_pages'][0]}\n\n{prompt_model_response_format}\n\nFor your output respond with the list of keywords that you want to use. Remember not to use any characters (e.g. newline) that cannot be encoded safely into JSON."""

    logger.info(cluster_selection_prompt)

    for _ in range(5):
        try:
            selected_cluster_json = lm.llama3_1_70b(cluster_selection_prompt)
            logger.info(f"selected_cluster_json: {selected_cluster_json}")
            selected_cluster = json.loads(selected_cluster_json)["output"]
            logger.info(f"selected_cluster: {selected_cluster}")
            break
        except Exception as e:
            logger.error(e)
            logger.error("Failed to get cluster selection, sleeping for 2 seconds...")
            time.sleep(2)
            continue


def generate_page(
    client_data: Dict[str, Any], cluster: List[str], all_sections, color_palette
) -> None:
    """
    Generates a page based on the data in client_data

    FIXME: what is "client_info"
    FIXME: what is "cluster"
    FIXME: what is "all_sections"
    FIXME: what is "color_palette"
    """

    prompt_model_response_format = """
            response_format: please output JSON with the following structure: 
            { 
                'assistant_analysis: 'write all of your analysis, thoughts, considerations, etc. here.', 
                'output': 'write your actual response to the prompt here' 
            }"""

    prompt_output_type = f"output_type: A json-wrapped html string, styled with tailwindcss using the following color palette: {color_palette}. Please remember to only use newline characters that can be properly encoded in json."
    page_html = ""
    section_prompt = ""

    for section in all_sections:
        # load text from path in each section object
        section_prompt = ""
        if type(section) is dict:
            prompt_path = f"/app/{section["path"]}"
            logger.info(prompt_path)
            section_prompt = open(prompt_path, "r").read()
        else:
            section_prompt = section

        section_prompt += f"We're going to make a website for the following company:\n\n{client_info}\n\nThe page we're writing focuses on these keywords:\n\n{cluster}\n\n{prompt_model_response_format}\n\n{prompt_output_type}\n\nhtml written so far:\n\n{page_html}"

        # send prompt to sonnet
        for _ in range(5):
            try:
                response = lm.sonnet(section_prompt, 4096)
                break
            except Exception as e:
                logger.error(e)
                logger.error("Failed to get response, sleeping for 2 seconds...")
                time.sleep(2)
                continue
        loaded_response = json.loads(response)
        page_html += loaded_response.get("output")

    return page_html
