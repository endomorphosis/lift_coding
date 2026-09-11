import importlib.metadata as md
for name in ('numpy','requests','spacy','faiss-cpu','transformers','openai'):
 try:
  dist=md.distribution(name)
  print(f'{name}\t{dist.version}\t{dist.locate_file("")}')
 except md.PackageNotFoundError:
  print(f'{name}\tabsent')
