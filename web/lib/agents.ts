export type Agent = {
  slug: string;
  name: string;
  description: string;
  mode: "query" | "upload";
  cta?: string;
};

export const AGENTS: Agent[] = [
  { slug: "hypothesis-generator", name: "Hypothesis Generator", description: "Convert your research ideas into strong hypotheses.", mode: "query", cta: "Start generating" },
  { slug: "hypothesis-evaluator", name: "Hypothesis Evaluator", description: "Evaluate your hypothesis to guide your research.", mode: "query", cta: "Evaluate" },
  { slug: "citation-recommender", name: "Citation Recommender", description: "Cite the right source for every sentence.", mode: "query", cta: "Generate citations" },
  { slug: "literature-review", name: "Literature Review", description: "Discover papers and developments for your research.", mode: "query", cta: "Start lit review" },
  { slug: "research-tracer", name: "Research Tracer", description: "Explore the path of research through citations.", mode: "query", cta: "Trace research" },
  { slug: "survey-simulator", name: "Survey Simulator", description: "Preview your survey results with AI respondents.", mode: "upload", cta: "Upload your survey" },
  { slug: "peer-review", name: "Peer Review", description: "Get expert-level peer review in minutes.", mode: "upload", cta: "Upload your paper" },
];
