FROM public.ecr.aws/docker/library/rust:latest

WORKDIR /usr/src/actuary
COPY . .

RUN cargo build --release
RUN chmod +x script/entrypoint.sh

ENTRYPOINT ["script/entrypoint.sh"]


