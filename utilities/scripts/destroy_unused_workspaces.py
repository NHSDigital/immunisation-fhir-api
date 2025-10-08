import subprocess
import os


def execute_terraform_command(command, cwd=None):
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"Error executing command: {command}")
            print(f"Error details: {stderr}")

        return process.returncode, stdout, stderr
    except Exception as e:
        print(f"Exception executing command: {command}")
        print(f"Exception details: {e}")
        return 1, None, str(e)


def set_env(aws_profile):
    # Create the path to the terraform directory
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the parent directory
    parent_directory = os.path.join(current_directory, "..")
    # Construct the path to the "terraform" directory
    terraform_directory = os.path.join(parent_directory, "terraform")
    # Change the working directory to the "terraform" directory
    os.chdir(terraform_directory)
    os.environ["AWS_PROFILE"] = aws_profile
    # Now you are in the terraform directory
    print("Terraform Directory:", os.getcwd())


def list_pr_workspaces(prefix):
    list_command = "terraform workspace list"
    print(list_command)

    return_code, stdout, stderr = execute_terraform_command(
        list_command, cwd=os.getcwd()
    )
    if return_code == 0:
        workspaces = stdout.strip().split("\n")
        print(f"Workspaces from Terraform: {workspaces}")
        # Filter workspaces that contain "pr" and replace spaces
        pr_workspaces = [
            workspace.replace(" ", "").replace("*", "")
            for workspace in workspaces
            if prefix in workspace.lower()
        ]
        return pr_workspaces
    else:
        print(f"Error listing workspaces: {stderr}")
        return []


def destroy_workspace(workspace_name, project_name, project_short_name):
    command_select = f"terraform workspace select {workspace_name}"
    tf_vars = (
        f"-var=project_name={project_name} "
        f"-var=project_short_name={project_short_name} "
    )
    command_destroy = f"terraform destroy {tf_vars} -auto-approve"
    command_delete = f"terraform workspace select default && terraform workspace delete {workspace_name}"

    try:
        # Command: terraform workspace select
        print(command_select)
        return_code_select, stdout_select, stderr_select = execute_terraform_command(
            command_select
        )
        if return_code_select != 0:
            print(f"Error executing select command for workspace {workspace_name}")
            return return_code_select, stdout_select, stderr_select

        # Command: terraform destroy
        print(command_destroy)
        return_code_destroy, stdout_destroy, stderr_destroy = execute_terraform_command(
            command_destroy
        )
        if return_code_destroy != 0:
            print(f"Error executing destroy command for workspace {workspace_name}")
            return return_code_destroy, stdout_destroy, stderr_destroy

        # Command: terraform workspace delete
        print(command_delete)
        return_code_delete, stdout_delete, stderr_delete = execute_terraform_command(
            command_delete
        )
        if return_code_delete != 0:
            print(f"Error executing delete command for workspace {workspace_name}")
            return return_code_delete, stdout_delete, stderr_delete
        else:
            print(f"Workspace {workspace_name} successfully deleted")

        return 0, "Destroyed successfully", None
    except Exception as e:
        return 1, None, str(e)


def destroy_workspace_wrapper(workspace_name, project_name, project_short_name):
    try:
        # Retry the destroy command if it returns non-zero exit code
        for _ in range(2):  # You can adjust the number of retries as needed
            return_code, stdout, stderr = destroy_workspace(
                workspace_name, project_name, project_short_name
            )
            if return_code == 0:
                return workspace_name, "Destroyed successfully"
            else:
                print(f"Retrying destroy command for workspace: {workspace_name}")
        return workspace_name, stderr
    except Exception as e:
        return workspace_name, str(e)


def main():
    project_name = "immunisation"
    project_short_name = "imms"
    aws_profile = "apim-dev"

    set_env(aws_profile)
    results = []
    # List workspaces
    workspaces = list_pr_workspaces("pr")
    print(f"Available Workspaces: {workspaces}")
    # Store results for all workspaces
    for workspace in workspaces:
        workspace_name, result = destroy_workspace_wrapper(
            workspace, project_name, project_short_name
        )
        results.append((workspace_name, result))

    # Print results at the end
    print("Results:")
    for workspace_name, result in results:
        print(f"Workspace: {workspace_name}, Result: {result}")


if __name__ == "__main__":
    main()
