FROM python:2-stretch

ENV USER=citus

RUN groupadd -r ${USER} --gid=1729
RUN useradd -mg ${USER} --uid=1729 --shell=/bin/bash ${USER}

RUN apt-get update && apt-get install -y \
    openssh-server \
    sudo 

USER ${USER}
WORKDIR /home/${USER}

RUN git clone --branch refactorArchitecture https://github.com/citusdata/test-automation.git

RUN pip install -r $HOME/test-automation/fabfile/requirements.txt --user

RUN echo 'source ${HOME}/test-automation/cloudformation/fab' >> ${HOME}/.bashrc

# add local bin so that we can use fab
RUN echo 'export PATH=${HOME}/.local/bin/:$PATH' >> ${HOME}/.bashrc

RUN ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile

EXPOSE 22 

USER root

COPY container_scripts /tmp

RUN set -ex; \
    ln -s /tmp/* /usr/local/bin;
