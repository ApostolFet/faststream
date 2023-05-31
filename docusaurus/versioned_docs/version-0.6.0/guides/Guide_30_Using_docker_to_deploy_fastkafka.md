Deploying FastKafka using Docker
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Building a Docker Image

To build a Docker image for a FastKafka project, we need the following
items:

1.  A library that is built using FastKafka.
2.  A file in which the requirements are specified. This could be a
    requirements.txt file, a setup.py file, or even a wheel file.
3.  A Dockerfile to build an image that will include the two files
    mentioned above.

### Creating FastKafka Code

Let’s create a
[`FastKafka`](../api/fastkafka/FastKafka.md/#fastkafka.FastKafka)-based
application and write it to the `application.py` file based on the
[tutorial](/docs#tutorial).

``` python
# content of the "application.py" file

from contextlib import asynccontextmanager

from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression

from fastkafka import FastKafka

ml_models = {}


@asynccontextmanager
async def lifespan(app: FastKafka):
    # Load the ML model
    X, y = load_iris(return_X_y=True)
    ml_models["iris_predictor"] = LogisticRegression(random_state=0, max_iter=500).fit(
        X, y
    )
    yield
    # Clean up the ML models and release the resources
    ml_models.clear()


from pydantic import BaseModel, NonNegativeFloat, Field

class IrisInputData(BaseModel):
    sepal_length: NonNegativeFloat = Field(
        ..., example=0.5, description="Sepal length in cm"
    )
    sepal_width: NonNegativeFloat = Field(
        ..., example=0.5, description="Sepal width in cm"
    )
    petal_length: NonNegativeFloat = Field(
        ..., example=0.5, description="Petal length in cm"
    )
    petal_width: NonNegativeFloat = Field(
        ..., example=0.5, description="Petal width in cm"
    )


class IrisPrediction(BaseModel):
    species: str = Field(..., example="setosa", description="Predicted species")

from fastkafka import FastKafka

kafka_brokers = {
    "localhost": {
        "url": "localhost",
        "description": "local development kafka broker",
        "port": 9092,
    },
    "production": {
        "url": "kafka.airt.ai",
        "description": "production kafka broker",
        "port": 9092,
        "protocol": "kafka-secure",
        "security": {"type": "plain"},
    },
}

kafka_app = FastKafka(
    title="Iris predictions",
    kafka_brokers=kafka_brokers,
    lifespan=lifespan,
)

@kafka_app.consumes(topic="input_data", auto_offset_reset="latest")
async def on_input_data(msg: IrisInputData):
    species_class = ml_models["iris_predictor"].predict(
        [[msg.sepal_length, msg.sepal_width, msg.petal_length, msg.petal_width]]
    )[0]

    await to_predictions(species_class)


@kafka_app.produces(topic="predictions")
async def to_predictions(species_class: int) -> IrisPrediction:
    iris_species = ["setosa", "versicolor", "virginica"]

    prediction = IrisPrediction(species=iris_species[species_class])
    return prediction
```

### Creating requirements.txt file

The above code only requires `fastkafka`. So, we will add only
`fastkafka` to the `requirements.txt` file, but you can add additional
requirements to it as well.

``` txt
fastkafka>=0.3.0
```

Here we are using `requirements.txt` to store the project’s
dependencies. However, other methods like `setup.py`, `pipenv`, and
`wheel` files can also be used. `setup.py` is commonly used for
packaging and distributing Python modules, while `pipenv` is a tool used
for managing virtual environments and package dependencies. `wheel`
files are built distributions of Python packages that can be installed
with pip.

### Creating Dockerfile

``` dockerfile
# (1)
FROM python:3.9-slim-bullseye
# (2)
WORKDIR /project
# (3)
COPY application.py requirements.txt /project/
# (4)
RUN pip install --no-cache-dir --upgrade -r /project/requirements.txt
# (5)
CMD ["fastkafka", "run", "--num-workers", "2", "--kafka-broker", "production", "application:kafka_app"]
```

1.  Start from the official Python base image.

2.  Set the current working directory to `/project`.

    This is where we’ll put the `requirements.txt` file and the
    `application.py` file.

3.  Copy the `application.py` file and `requirements.txt` file inside
    the `/project` directory.

4.  Install the package dependencies in the requirements file.

    The `--no-cache-dir` option tells `pip` to not save the downloaded
    packages locally, as that is only if `pip` was going to be run again
    to install the same packages, but that’s not the case when working
    with containers.

    The `--upgrade` option tells `pip` to upgrade the packages if they
    are already installed.

5.  Set the **command** to run the `fastkafka run` command.

    `CMD` takes a list of strings, each of these strings is what you
    would type in the command line separated by spaces.

    This command will be run from the **current working directory**, the
    same `/project` directory you set above with `WORKDIR /project`.

    We supply additional parameters `--num-workers` and `--kafka-broker`
    for the run command. Finally, we specify the location of our
    `fastkafka` application location as a command argument.

    To learn more about `fastkafka run` command please check the [CLI
    docs](../cli/fastkafka/#fastkafka-run).

### Build the Docker Image

Now that all the files are in place, let’s build the container image.

1.  Go to the project directory (where your `Dockerfile` is, containing
    your `application.py` file).

2.  Run the following command to build the image:

    ``` cmd
    docker build -t fastkafka_project_image .
    ```

    This command will create a docker image with the name
    `fastkafka_project_image` and the `latest` tag.

That’s it! You have now built a docker image for your FastKafka project.

### Start the Docker Container

Run a container based on the built image:

``` cmd
docker run -d --name fastkafka_project_container fastkafka_project_image
```

## Additional Security

`Trivy` is an open-source tool that scans Docker images for
vulnerabilities. It can be integrated into your CI/CD pipeline to ensure
that your images are secure and free from known vulnerabilities. Here’s
how you can use `trivy` to scan your `fastkafka_project_image`:

1.  Install `trivy` on your local machine by following the instructions
    provided in the [official `trivy`
    documentation](https://aquasecurity.github.io/trivy/latest/getting-started/installation/).

2.  Run the following command to scan your fastkafka_project_image:

    ``` cmd
    trivy image fastkafka_project_image
    ```

    This command will scan your `fastkafka_project_image` for any
    vulnerabilities and provide you with a report of its findings.

3.  Fix any vulnerabilities identified by `trivy`. You can do this by
    updating the vulnerable package to a more secure version or by using
    a different package altogether.

4.  Rebuild your `fastkafka_project_image` and repeat steps 2 and 3
    until `trivy` reports no vulnerabilities.

By using `trivy` to scan your Docker images, you can ensure that your
containers are secure and free from known vulnerabilities.

## Example repo

A
[`FastKafka`](../api/fastkafka/FastKafka.md/#fastkafka.FastKafka)
based library which uses above mentioned Dockerfile to build a docker
image can be found
[here](https://github.com/airtai/sample_fastkafka_project/)