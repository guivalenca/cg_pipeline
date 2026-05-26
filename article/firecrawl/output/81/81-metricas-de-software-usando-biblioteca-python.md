---
id: "81"
title: "Métricas de Software usando Biblioteca Python"
source_url: "https://github.com/elmotec/codemetrics"
fetch_url: "https://github.com/elmotec/codemetrics"
resolved_url: "https://github.com/elmotec/codemetrics"
firecrawl_title: "GitHub - elmotec/codemetrics: Multi language library for pandas notebook to mine git and gain insights on your code base. · GitHub"
description: "Multi language library for pandas notebook to mine git and gain insights on your code base. - elmotec/codemetrics"
fetched_at: "2026-05-12T03:59:53.001917Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "38c6511b4f19d24e74d10f34631801bef42feaf787b2a4c80caf6461ea6b21e5"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 334
char_count: 2483
content_sha256: "a4d287aa6e9cb9d224e5c7e61241079987aac37aa7f842235e7ae2029a4cefeb"
image_count: 14
link_count: 86
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "github_app_ui_or_wrapper_page"
---

## codemetrics

Mine your SCM for insight on your software. A work of love inspired by [Adam Tornhill](https://www.adamtornhill.com/)'s books.

Code metrics is a simple Python module that leverage pandas and your source control management (SCM) tool to generate insight on your code base.

- [pandas](https://pandas.pydata.org/): for data munching.
- [lizard](https://github.com/terryyin/lizard): for code complexity calculation.
- cloc.pl (script): for line counts from [cloc](http://cloc.sourceforge.net/)
- For now, only Subversion and git are supported.

### Installation

To install codemetrics, simply use pip:

```
pip install codemetrics
```

### Usage

This is a simple tool that makes it easy to retrieve information from your Source Control Management (SCM) repository and hopefully gain insight from it.

```
import codemetrics as cm
import cm.git

project = cm.GitProject('path/to/project')
loc_df = cm.get_cloc(project, cloc_program='/path/to/cloc')
log_df = cm.get_log(project)
ages_df = cm.get_ages(log_df)
```

To retrieve the number of lines changed by revision with Subversion:

```
import codemetrics as cm
import cm.git

project = cm.SvnProject('path/to/project')
log_df = cm.get_log(project).set_index(['revision', 'path'])
log_df.loc[:, ['added', 'removed']] = log_df.reset_index().\
                                         groupby('revision').\
                                         apply(cm.svn.get_diff_stats, chunks=False)
```

See [module documentation](https://codemetrics.readthedocs.org/) for more advanced functions or the [example notebook](https://github.com/elmotec/codemetrics/blob/main/notebooks/pandas.ipynb) where codemetrics is applied to pandas.

### License

Licensed under the term of [MIT License](https://en.wikipedia.org/wiki/MIT_License). See attached file LICENSE.txt.

### Credits

- This package was inspired by [Adam Tornhill](https://www.adamtornhill.com/)'s books.
- This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter).

## About

Multi-language library for pandas notebook to mine git and gain insights on your code base.

### Topics

[analysis](https://github.com/topics/analysis "Topic: analysis") [code](https://github.com/topics/code "Topic: code") [metrics](https://github.com/topics/metrics "Topic: metrics")

### License

[MIT license](https://github.com/elmotec/codemetrics#MIT-1-ov-file)

### Contributing

[Contributing](https://github.com/elmotec/codemetrics#contributing-ov-file)
