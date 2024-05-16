<h1 style="display: flex; align-items: center; gap: 4;">
  <img style="display: inline-block;" width="42" height="auto" loading="lazy" alt="LociGraph Icon" src="{{ '/assets/icon.png' | relative_url }}">
  Locigraph
</h1>

> AI Agent Framework for Browser-Based Knowledge Graph Construction

[Paper](https://dub.sh/locigraph-paper) \| [Code](https://dub.sh/locigraph) \| [Demo](https://dub.sh/locigraph-demo) \| [Author](https://ntcho.me)

<iframe style="width: 100%; aspect-ratio: 16 / 9;" src="https://www.youtube-nocookie.com/embed/ZYut9qmtAlk?si=71ksIIhLfh_aDQEx" title="LociGraph Video Demo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## *Browser-based knowledge graph construction*: What is it exactly?

*Browser-based knowledge graph construction* is a task where an agent browses the web using the user's browser to find a webpage containing the relevant information and constructs a knowledge graph.

For example, if the agent is given the query `[Alex, studied at, ?]` on your email inbox, the agent will start by typing “*Alex*” into the search bar, click on email related to Alex, read the content “*Alex went to Bard College*” and return `[Alex, studied at, Bard College]`.

## Why do we need this?

Each person interacts with hundreds of webpages every day. Between hundreds of webpages, information is stored in hundreds of different unstructured formats (e.g., email, messages, posts, and social media profiles). This lack of structure and separation of data makes it very difficult to manage information in a centralized and organized way.

While information on the public web (e.g. Wikipedia) can be easily accessed using search engines, non-public webpages (e.g., email inbox, online community, social media) need to be manually visited. This framework makes the computer do the repetitive clicking and typing for you.

## How does this work?

The framework consists of two parts: an *agent pipeline*, where a group of agents analyze the webpage content and suggest the next action, and a *browser extension*, where the user can enter the query and execute the suggested action.

The agent pipeline is implemented as an API server using [litestar](https://litestar.dev/), receiving requests from the browser extension over HTTP connections and processing the pipeline in the backend. The browser extension is implemented using [Plasmo](https://www.plasmo.com/) and uses the [Chrome DevTools protocol](https://chromedevtools.github.io/devtools-protocol/) to execute the actions predicted by the agent pipeline.

## Can we download LociGraph now?

The browser extension will be released on GitHub later this year. In the meantime, you can build the browser extension on your own using `pnpm build` in the `src/client` directory and run the agent pipeline using `make start && make start-models` in the `src/server` directory.
