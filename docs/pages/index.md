<img align="left" width="48" height="auto" loading="lazy" alt="LociGraph icon" src="{{ '/assets/icon.png' | relative_url }}">

# LociGraph

> AI Agent Framework for Browser-based Knowledge Graph Construction

[Nathan Cho](https://ntcho.me)

[Paper](https://dub.sh/locigraph-paper) | [Code](https://dub.sh/locigraph) | [Demo](https://dub.sh/locigraph-demo)

## About LociGraph

**LociGraph** is an AI agent framework for *browser-based knowledge graph construction*.

<!-- <img loading="lazy" alt="Example of ai tasks" src="{{ '/assets/images/examples/ai.1.oyuiubm.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of booking tasks" src="{{ '/assets/images/examples/booking.1.pxtuocd.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of composing tasks" src="{{ '/assets/images/examples/composing.1.tbtnzql.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of lookup tasks" src="{{ '/assets/images/examples/lookup.1.zbrxcee.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of productivity tasks" src="{{ '/assets/images/examples/productivity.1.ytcgitj.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of shopping tasks" src="{{ '/assets/images/examples/shopping.1.wbamufj.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of social tasks" src="{{ '/assets/images/examples/social.1.xmrqcyz.webp' | relative_url }}" width="24%" height="auto">
<img loading="lazy" alt="Example of summarizing tasks" src="{{ '/assets/images/examples/summarizing.1.bctdmtt.webp' | relative_url }}" width="24%" height="auto"> -->

## *Browser-based knowledge graph construction*: What is it exactly?

*Browser-based knowledge graph construction* is a task where an agent browses the web using the user's browser to find a webpage containing the relevant information and constructs a knowledge graph.

## Can we download LociGraph now?

Packaged browser extension will be released in the future on GitHub. In the meantime, you can build the browser extension on your own using `pnpm build` in the `src/client` directory.


## How do we use the agent to control browsers?

We use Chrome DevTools protocol to control the browser. More detail on this will be added in the future here.

<!-- ## How do we cite WebLINX?

If you use our dataset, code, or models, please use the following `bibtex` citation entry:

```bibtex
@misc{lù2024weblinx,
      title={WebLINX: Real-World Website Navigation with Multi-Turn Dialogue}, 
      author={Xing Han Lù and Zdeněk Kasner and Siva Reddy},
      year={2024},
      eprint={2402.05930},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
``` -->