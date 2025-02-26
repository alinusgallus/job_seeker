from crewai import Agent, Crew, Process, Task   
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeElementFromWebsiteTool, FileReadTool
from crewai.llm import LLM
import yaml
from pathlib import Path



ollama_llm = LLM(
	model="ollama/custom_llama",
	api_base="http://localhost:11434",
)


tools = [
    FileReadTool(),
    ScrapeElementFromWebsiteTool()
]

@CrewBase
class ResumeJobMatcher():
    """ResumeJobMatcher crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, inputs=None):
        self.inputs = inputs or {}
        super().__init__()

    @agent
    def resume_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['resume_analyst'],
            system_prompt=(
                "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                "Cutting Knowledge Date: December 2023\n"
                "Today Date: 17 February 2025\n"
                "You are an expert resume reviewer. Analyze resumes to identify strengths, weaknesses, and key qualifications.\n"
                "<|eot_id|>"
            ),
            llm=ollama_llm,
            verbose=True
        )

    @agent
    def job_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['job_analyst'],
            system_prompt=(
                "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                "Cutting Knowledge Date: December 2023\n"
                "Today Date: 17 February 2025\n"
                "You are an expert job requirements analyst. Analyze job descriptions to extract key requirements and priorities.\n"
                "<|eot_id|>"
            ),
            llm=ollama_llm,
            verbose=True
        )

    @agent
    def matching_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['matching_specialist'],
            system_prompt=(
                "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                "Cutting Knowledge Date: December 2023\n"
                "Today Date: 17 February 2025\n"
                "You are a skills matching specialist. Analyze how well a candidate's qualifications match job requirements.\n"
                "<|eot_id|>"
            ),  
            llm=ollama_llm,
            verbose=True
        )

    @task
    def resume_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['resume_analysis_task']
        )

    @task
    def job_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['job_analysis_task']
        )

    @task
    def matching_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['matching_analysis_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ResumeJobMatcher crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,    # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )

